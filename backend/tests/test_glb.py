import json
import re
import struct
from collections.abc import Callable

import pytest

from backend.app.config import REPO_ROOT
from backend.app.db import timestamp
from backend.app.errors import AppError
from backend.app.glb import validate_glb

FIXTURE = (REPO_ROOT / "fixtures" / "sample-cube.glb").read_bytes()


def rewrite(content: bytes, mutate: Callable[[dict], None]) -> bytes:
    json_length = struct.unpack_from("<I", content, 12)[0]
    model = json.loads(content[20 : 20 + json_length])
    binary_chunk = content[20 + json_length :]
    mutate(model)
    metadata = json.dumps(model, separators=(",", ":")).encode()
    metadata += b" " * (-len(metadata) % 4)
    header = struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(metadata) + len(binary_chunk))
    return header + struct.pack("<II", len(metadata), 0x4E4F534A) + metadata + binary_chunk


def test_fixture_is_valid():
    assert validate_glb(FIXTURE)["triangles"] == 12


@pytest.mark.parametrize(
    "mutate",
    [
        lambda model: model["accessors"][0].__setitem__("bufferView", -1),
        lambda model: model["accessors"][0].__setitem__("bufferView", True),
        lambda model: model["meshes"][0]["primitives"][0]["attributes"].__setitem__("POSITION", -1),
        lambda model: model["meshes"][0]["primitives"][0].__setitem__("indices", 99),
        lambda model: model.__setitem__("scene", -1),
    ],
)
def test_rejects_out_of_range_indices(mutate):
    with pytest.raises(AppError, match="無法開啟"):
        validate_glb(rewrite(FIXTURE, mutate))


def test_timestamp_is_fixed_width_and_sortable():
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z", timestamp())
