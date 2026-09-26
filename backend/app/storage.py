import os
import re
import tempfile
from pathlib import Path


class LocalStorage:
    """Private files accessed through an authorized API, never a static mount."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root.chmod(0o700)

    def path(self, key: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}\.(png|jpg|glb)", key):
            raise ValueError("Invalid storage key")
        path = (self.root / key).resolve()
        if path.parent != self.root:
            raise ValueError("Storage key escaped private storage")
        return path

    def write(self, key: str, content: bytes) -> Path:
        target = self.path(key)
        descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=self.root)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return target

    def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)
