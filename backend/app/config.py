"""Local-only configuration. No environment file or provider secrets are loaded."""

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    local_owner: str = "local-owner"
    worker_interval: float = 0.5
    lease_seconds: float = 30.0
    max_attempts: int = 5
    retry_seconds: float = 2.0
    web_origin: str = "http://127.0.0.1:5173"

    @classmethod
    def from_environment(cls) -> "Settings":
        data_dir = Path(os.getenv("PTM_DATA_DIR", "output/data")).expanduser()
        if not data_dir.is_absolute():
            data_dir = REPO_ROOT / data_dir
        owner = os.getenv("PTM_LOCAL_OWNER", "local-owner").strip()
        if not owner:
            raise ValueError("PTM_LOCAL_OWNER must not be empty")
        web_origin = os.getenv("PTM_WEB_ORIGIN", "http://127.0.0.1:5173").rstrip("/")
        origin = urlsplit(web_origin)
        if (
            origin.scheme != "http"
            or origin.hostname not in {"127.0.0.1", "localhost", "::1"}
            or origin.path
            or origin.query
            or origin.fragment
            or origin.username
        ):
            raise ValueError("PTM_WEB_ORIGIN must be an explicit local HTTP origin")
        return cls(data_dir=data_dir.resolve(), local_owner=owner, web_origin=web_origin)

    @property
    def database_path(self) -> Path:
        return self.data_dir / "database.sqlite3"

    @property
    def assets_dir(self) -> Path:
        return self.data_dir / "assets"
