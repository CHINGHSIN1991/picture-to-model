import pytest

from backend.app.config import REPO_ROOT, Settings
from backend.app.glb import validate_glb
from backend.app.providers import FakeProvider


def test_defaults_and_relative_data_paths_are_independent_of_working_directory(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    for key in ("PTM_DATA_DIR", "PTM_LOCAL_OWNER", "PTM_WEB_ORIGIN"):
        monkeypatch.delenv(key, raising=False)
    assert Settings.from_environment().data_dir == REPO_ROOT / "output" / "data"
    monkeypatch.setenv("PTM_DATA_DIR", "output/relative-test")
    assert Settings.from_environment().data_dir == REPO_ROOT / "output" / "relative-test"
    provider = FakeProvider()
    assert provider.fixture.is_file()
    assert validate_glb(provider.fetch_result("fake:default-fixture"))["triangles"] == 12


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.example",
        "http://localhost.evil.example:5173",
        "http://127.0.0.1:5173/path",
        "http://localhost:5173?query=yes",
        "http://localhost:5173#fragment",
        "http://user@localhost:5173",
        "http://@localhost:5173",
        "http://localhost:invalid",
        "http://localhost:65536",
    ],
)
def test_startup_rejects_nonlocal_or_malformed_web_origins(monkeypatch, origin):
    monkeypatch.setenv("PTM_WEB_ORIGIN", origin)
    with pytest.raises(ValueError, match="PTM_WEB_ORIGIN"):
        Settings.from_environment()


@pytest.mark.parametrize(
    "origin", ["http://127.0.0.1:15173", "http://localhost:5173", "http://[::1]:5173"]
)
def test_startup_accepts_explicit_local_web_origins(monkeypatch, origin):
    monkeypatch.setenv("PTM_WEB_ORIGIN", origin)
    assert Settings.from_environment().web_origin == origin


def test_startup_rejects_empty_owner(monkeypatch):
    monkeypatch.setenv("PTM_LOCAL_OWNER", "  ")
    with pytest.raises(ValueError, match="PTM_LOCAL_OWNER"):
        Settings.from_environment()
