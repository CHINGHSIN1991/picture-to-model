"""Bounded validation for our static, self-contained fixture GLB.

This deliberately small validator is not a replacement for glTF Validator before
accepting real provider results and user exports in subsequent phases.
"""

import json
import struct
from typing import Any

from .errors import AppError

MAX_MODEL_BYTES = 100 * 1024 * 1024


def validate_glb(content: bytes) -> dict[str, int]:
    try:
        return _validate(content)
    except (ValueError, KeyError, IndexError, TypeError, struct.error, UnicodeDecodeError) as error:
        raise AppError("invalid_model", "模型不是支援的自包含靜態 GLB，無法開啟。") from error


def _item(sequence: list, index: Any) -> Any:
    """Bounded lookup for untrusted JSON indices: no negatives, bools, or wraparound."""
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(sequence):
        raise ValueError("Index out of range")
    return sequence[index]


def _validate(content: bytes) -> dict[str, int]:
    if not 28 <= len(content) <= MAX_MODEL_BYTES:
        raise ValueError("Model size out of bounds")
    magic, version, length = struct.unpack_from("<4sII", content)
    if magic != b"glTF" or version != 2 or length != len(content):
        raise ValueError("Invalid GLB header")
    chunks: list[tuple[int, bytes]] = []
    offset = 12
    while offset < length:
        size, kind = struct.unpack_from("<II", content, offset)
        offset += 8
        if size % 4 or offset + size > length:
            raise ValueError("Invalid chunk bounds")
        chunks.append((kind, content[offset : offset + size]))
        offset += size
    if offset != length or len(chunks) != 2:
        raise ValueError("Expected JSON and BIN chunks")
    if chunks[0][0] != 0x4E4F534A or chunks[1][0] != 0x004E4942:
        raise ValueError("Invalid chunk order")
    model = json.loads(chunks[0][1])
    binary = chunks[1][1]
    if model["asset"]["version"] != "2.0":
        raise ValueError("Unsupported glTF version")
    if model.get("extensionsRequired") or model.get("animations") or model.get("skins"):
        raise ValueError("Unsupported extension, animation, or skin")

    def check_uris(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "uri":
                    raise ValueError("External and data URI resources are not allowed")
                check_uris(child)
        elif isinstance(value, list):
            for child in value:
                check_uris(child)

    check_uris(model)
    buffers = model["buffers"]
    if len(buffers) != 1 or not 0 <= len(binary) - buffers[0]["byteLength"] <= 3:
        raise ValueError("Invalid embedded buffer")
    views = model["bufferViews"]
    for view in views:
        start, size = view.get("byteOffset", 0), view["byteLength"]
        if view["buffer"] != 0 or start < 0 or size <= 0:
            raise ValueError("Invalid buffer view")
        if start + size > buffers[0]["byteLength"]:
            raise ValueError("Buffer view out of bounds")
    accessors = model["accessors"]
    components = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
    shapes = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
    for accessor in accessors:
        if accessor.get("sparse"):
            raise ValueError("Sparse accessors are not yet supported")
        view = _item(views, accessor["bufferView"])
        size = components[accessor["componentType"]] * shapes[accessor["type"]]
        count, start = accessor["count"], accessor.get("byteOffset", 0)
        stride = view.get("byteStride", size)
        if count <= 0 or start < 0 or stride < size:
            raise ValueError("Invalid accessor")
        if start + (count - 1) * stride + size > view["byteLength"]:
            raise ValueError("Accessor out of bounds")
    triangles = 0
    for mesh in model["meshes"]:
        for primitive in mesh["primitives"]:
            if primitive.get("mode", 4) != 4:
                raise ValueError("Only triangle meshes supported")
            position = _item(accessors, primitive["attributes"]["POSITION"])
            if position["type"] != "VEC3" or position["componentType"] != 5126:
                raise ValueError("Invalid position accessor")
            if "indices" in primitive:
                indices = _item(accessors, primitive["indices"])
                valid_index_types = (5121, 5123, 5125)
                if indices["type"] != "SCALAR" or indices["componentType"] not in valid_index_types:
                    raise ValueError("Invalid index accessor")
                count = indices["count"]
            else:
                count = position["count"]
            if count % 3:
                raise ValueError("Incomplete triangle")
            triangles += count // 3
    if not triangles or not _item(model["scenes"], model.get("scene", 0))["nodes"]:
        raise ValueError("Empty model")
    return {"triangles": triangles, "bytes": len(content)}
