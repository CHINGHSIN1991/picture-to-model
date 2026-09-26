"""Rebuild the self-authored, CC0 sample cube. Uses only the Python standard library."""

import json
import struct
from pathlib import Path


def create_cube() -> bytes:
    faces = [
        ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
        ((0, 0, -1), [(1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)]),
        ((1, 0, 0), [(1, -1, 1), (1, -1, -1), (1, 1, -1), (1, 1, 1)]),
        ((-1, 0, 0), [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)]),
        ((0, 1, 0), [(-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1)]),
        ((0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)]),
    ]
    positions, normals, indices = [], [], []
    for normal, vertices in faces:
        start = len(positions) // 3
        for vertex in vertices:
            positions.extend(value * 0.5 for value in vertex)
            normals.extend(normal)
        indices.extend(start + index for index in [0, 1, 2, 0, 2, 3])
    binary = struct.pack(f"<{len(positions)}f", *positions)
    binary += struct.pack(f"<{len(normals)}f", *normals)
    binary += struct.pack(f"<{len(indices)}H", *indices)
    model = {
        "asset": {"version": "2.0", "generator": "Picture to Model self-authored fixture"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "Sample cube", "mesh": 0}],
        "meshes": [
            {
                "name": "Cube",
                "primitives": [
                    {
                        "attributes": {"POSITION": 0, "NORMAL": 1},
                        "indices": 2,
                        "material": 0,
                    }
                ],
            }
        ],
        "materials": [
            {
                "name": "Teal ceramic",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.08, 0.58, 0.53, 1.0],
                    "metallicFactor": 0.12,
                    "roughnessFactor": 0.35,
                },
            }
        ],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 288, "target": 34962},
            {"buffer": 0, "byteOffset": 288, "byteLength": 288, "target": 34962},
            {"buffer": 0, "byteOffset": 576, "byteLength": 72, "target": 34963},
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": 24,
                "type": "VEC3",
                "min": [-0.5, -0.5, -0.5],
                "max": [0.5, 0.5, 0.5],
            },
            {"bufferView": 1, "componentType": 5126, "count": 24, "type": "VEC3"},
            {"bufferView": 2, "componentType": 5123, "count": 36, "type": "SCALAR"},
        ],
    }
    metadata = json.dumps(model, separators=(",", ":")).encode()
    metadata += b" " * (-len(metadata) % 4)
    binary += b"\x00" * (-len(binary) % 4)
    return (
        struct.pack("<4sII", b"glTF", 2, 28 + len(metadata) + len(binary))
        + struct.pack("<II", len(metadata), 0x4E4F534A)
        + metadata
        + struct.pack("<II", len(binary), 0x004E4942)
        + binary
    )


if __name__ == "__main__":
    Path(__file__).with_name("sample-cube.glb").write_bytes(create_cube())
