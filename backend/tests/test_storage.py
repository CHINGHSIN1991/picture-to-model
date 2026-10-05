import os
import stat
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from backend.app.db import Database
from backend.app.storage import LocalStorage


@pytest.mark.parametrize("run", range(4))
def test_concurrent_initialization_of_fresh_database(tmp_path, run):
    path = tmp_path / str(run) / "database.sqlite3"
    barrier = Barrier(6)

    def initialize(_):
        database = Database(path)
        barrier.wait(timeout=10)
        database.initialize()
        with database.connect() as connection:
            assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(initialize, range(6)))
    with Database(path).connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0


def test_atomic_write_preserves_original_on_failure_and_cleans_temporary_file(
    tmp_path, monkeypatch
):
    storage = LocalStorage(tmp_path / "assets")
    key = "a" * 32 + ".glb"
    target = storage.write(key, b"original")

    def fail_replace(source, destination):
        raise OSError("Interrupted before atomic rename")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="Interrupted"):
        storage.write(key, b"replacement")
    assert target.read_bytes() == b"original"
    assert list(storage.root.iterdir()) == [target]
    assert stat.S_IMODE(storage.root.stat().st_mode) == 0o700
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


@pytest.mark.parametrize("key", ["../secret", "/tmp/secret", "a.glb", "a" * 32 + ".html"])
def test_storage_rejects_noncanonical_keys(tmp_path, key):
    with pytest.raises(ValueError, match="Invalid storage key"):
        LocalStorage(tmp_path / "assets").write(key, b"bad")


def test_storage_rejects_symlink_escape(tmp_path):
    storage = LocalStorage(tmp_path / "assets")
    outside = tmp_path / "outside.glb"
    outside.write_bytes(b"private")
    key = "b" * 32 + ".glb"
    (storage.root / key).symlink_to(outside)
    with pytest.raises(ValueError, match="escaped"):
        storage.write(key, b"overwrite")
    with pytest.raises(ValueError, match="escaped"):
        storage.delete(key)
    assert outside.read_bytes() == b"private"
