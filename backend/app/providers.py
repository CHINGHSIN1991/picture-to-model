from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from .config import REPO_ROOT


@dataclass(frozen=True)
class ProviderStatus:
    state: Literal["pending", "succeeded", "failed"]


class ModelProvider(Protocol):
    def submit(self, source: Path, request_key: str) -> str: ...

    def get_status(self, task_id: str) -> ProviderStatus: ...

    def fetch_result(self, task_id: str) -> bytes: ...


class FakeProvider:
    """Deterministic, restart-safe, zero-network fixture provider.

    Submit is idempotent on request_key, so a crash after submit can safely be
    replayed. This guarantee belongs to this fake adapter, not future paid APIs.
    """

    name = "fake"
    model = "fixture-v1"

    def __init__(self, fixture: Path | None = None):
        self.fixture = fixture or REPO_ROOT / "fixtures" / "sample-cube.glb"

    def submit(self, source: Path, request_key: str) -> str:
        if not source.is_file():
            raise FileNotFoundError("Source image no longer exists")
        return f"fake:{request_key}"

    def get_status(self, task_id: str) -> ProviderStatus:
        self._check_task(task_id)
        return ProviderStatus("succeeded")

    def fetch_result(self, task_id: str) -> bytes:
        self._check_task(task_id)
        return self.fixture.read_bytes()

    @staticmethod
    def _check_task(task_id: str) -> None:
        if not task_id.startswith("fake:") or not task_id[5:]:
            raise ValueError("Unknown fake task")
