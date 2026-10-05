"""Independent durable worker. Run with `python -m backend.app.worker`."""

import argparse
import hashlib
import json
import logging
import signal
import sqlite3
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from .config import Settings
from .db import Database, timestamp
from .errors import AppError
from .glb import validate_glb
from .providers import FakeProvider, ModelProvider
from .storage import LocalStorage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Claim:
    job_id: str
    generation_id: str
    token: str
    attempt: int  # Consecutive claims since the last successful stage or status poll.


class Worker:
    def __init__(
        self,
        settings: Settings,
        provider: ModelProvider | None = None,
        clock: Callable[[], float] = time.time,
    ):
        self.settings = settings
        self.database = Database(settings.database_path)
        self.database.initialize()
        self.storage = LocalStorage(settings.assets_dir)
        self.provider = provider or FakeProvider()
        self.clock = clock

    def claim(self) -> Claim | None:
        now = self.clock()
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT j.* FROM jobs j JOIN generations g ON g.id = j.generation_id "
                "WHERE j.status = 'pending' AND j.next_run_at <= ? "
                "AND (j.lease_expires_at IS NULL OR j.lease_expires_at <= ?) "
                "AND g.owner_id = ? ORDER BY j.next_run_at, j.created_at LIMIT 1",
                (now, now, self.settings.local_owner),
            ).fetchone()
            if row is None:
                return None
            token = uuid4().hex
            connection.execute(
                "UPDATE jobs SET lease_token = ?, lease_expires_at = ?, attempt = attempt + 1 "
                "WHERE id = ?",
                (token, now + self.settings.lease_seconds, row["id"]),
            )
            return Claim(row["id"], row["generation_id"], token, row["attempt"] + 1)

    def _holds_lease(self, connection: sqlite3.Connection, claim: Claim) -> bool:
        return (
            connection.execute(
                "SELECT 1 FROM jobs WHERE id = ? AND lease_token = ? AND lease_expires_at > ? "
                "AND status = 'pending'",
                (claim.job_id, claim.token, self.clock()),
            ).fetchone()
            is not None
        )

    def _release(
        self,
        connection: sqlite3.Connection,
        claim: Claim,
        status: str = "pending",
        delay: float | None = None,
        reset_attempt: bool = False,
    ):
        if delay is None:
            delay = self.settings.worker_interval
        connection.execute(
            "UPDATE jobs SET lease_token = NULL, lease_expires_at = NULL, status = ?, "
            "next_run_at = ?, attempt = CASE WHEN ? THEN 0 ELSE attempt END "
            "WHERE id = ? AND lease_token = ?",
            (status, self.clock() + delay, reset_attempt, claim.job_id, claim.token),
        )

    def _retry_later(self, claim: Claim) -> None:
        """Give the same stage back to the queue with backoff instead of failing it."""
        with self.database.transaction() as connection:
            if self._holds_lease(connection, claim):
                self._release(connection, claim, delay=self.settings.retry_seconds * claim.attempt)

    def _advance(self, claim: Claim, state: str, **fields: str) -> bool:
        allowed = {"provider_task_id", "result_storage_key", "error_code", "error_message"}
        if not fields.keys() <= allowed:
            raise ValueError("Unexpected generation field")
        with self.database.transaction() as connection:
            if not self._holds_lease(connection, claim):
                return False
            assignments = ", ".join(f"{field} = ?" for field in fields)
            if assignments:
                assignments = ", " + assignments
            connection.execute(
                f"UPDATE generations SET state = ?, updated_at = ?{assignments} WHERE id = ?",
                (state, timestamp(), *fields.values(), claim.generation_id),
            )
            # Successful stages and pending provider polls must not consume the
            # retry budget of the next operation. Crashes and failed calls do.
            self._release(
                connection,
                claim,
                "failed" if state == "failed" else "pending",
                reset_attempt=state != "failed",
            )
        logger.info("generation_id=%s state=%s", claim.generation_id, state)
        return True

    def _finish(self, claim: Claim, generation: sqlite3.Row, content: bytes, metrics: dict):
        with self.database.transaction() as connection:
            if not self._holds_lease(connection, claim):
                return
            asset_id, version_id = str(uuid4()), str(uuid4())
            now = timestamp()
            connection.execute(
                "INSERT INTO assets VALUES (?, ?, 'model', ?, ?, 'model/gltf-binary', ?, ?)",
                (
                    asset_id,
                    generation["project_id"],
                    generation["result_storage_key"],
                    hashlib.sha256(content).hexdigest(),
                    len(content),
                    now,
                ),
            )
            connection.execute(
                "INSERT INTO model_versions VALUES (?, ?, ?, ?, ?)",
                (version_id, generation["id"], asset_id, json.dumps(metrics), now),
            )
            connection.execute(
                "UPDATE generations SET state = 'ready', model_version_id = ?, updated_at = ? "
                "WHERE id = ?",
                (version_id, now, generation["id"]),
            )
            self._release(connection, claim, "completed", reset_attempt=True)
        logger.info("generation_id=%s state=ready", claim.generation_id)

    def process(self, claim: Claim) -> None:
        """Process one recoverable stage; commit only while holding the fencing token."""
        with self.database.connect() as connection:
            if not self._holds_lease(connection, claim):
                return
            generation = connection.execute(
                "SELECT g.*, a.storage_key AS source_key FROM generations g "
                "JOIN assets a ON a.id = g.source_asset_id WHERE g.id = ?",
                (claim.generation_id,),
            ).fetchone()
        try:
            state = generation["state"]
            if state == "queued":
                self._advance(claim, "submitting")
            elif state == "submitting":
                # The fake adapter is idempotent on generation ID, including a
                # restart after the adapter accepts submit but before DB commit.
                task_id = self.provider.submit(
                    self.storage.path(generation["source_key"]), generation["id"]
                )
                self._advance(claim, "generating", provider_task_id=task_id)
            elif state == "generating":
                result = self.provider.get_status(generation["provider_task_id"])
                if result.state == "failed":
                    raise AppError("provider_failed", "模擬生成失敗，請建立新的任務。")
                self._advance(claim, "downloading" if result.state == "succeeded" else "generating")
            elif state == "downloading":
                content = self.provider.fetch_result(generation["provider_task_id"])
                # A unique candidate per claim prevents a stale worker from
                # replacing bytes committed by a replacement worker.
                key = f"{uuid4().hex}.glb"
                self.storage.write(key, content)
                if not self._advance(claim, "validating", result_storage_key=key):
                    self.storage.delete(key)
            elif state == "validating":
                content = self.storage.path(generation["result_storage_key"]).read_bytes()
                self._finish(claim, generation, content, validate_glb(content))
            else:
                raise AppError("invalid_job_state", "任務狀態無法處理。")
        except AppError as error:
            self._advance(claim, "failed", error_code=error.code, error_message=error.message)
        except Exception as error:
            # Infrastructure errors (locked DB, transient I/O) are retried on the same
            # stage; only repeated failures dead-end the generation.
            logger.error(
                "generation_id=%s attempt=%s failure=%s",
                claim.generation_id,
                claim.attempt,
                type(error).__name__,
            )
            if claim.attempt < self.settings.max_attempts:
                self._retry_later(claim)
                return
            self._advance(
                claim,
                "failed",
                error_code="generation_failed",
                error_message="模擬生成多次未完成，請確認來源圖片及範例模型存在後建立新的任務。",
            )

    def run_once(self) -> bool:
        claim = self.claim()
        if claim is None:
            return False
        self.process(claim)
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local fake-generation worker")
    parser.add_argument("--once", action="store_true", help="Process one due stage, then exit")
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    worker = Worker(Settings.from_environment())
    if arguments.once:
        worker.run_once()
        return
    stopped = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stopped.set())
    logger.info("Local fake-provider worker started")
    while not stopped.is_set():
        try:
            worker.run_once()
        except sqlite3.OperationalError as error:
            logger.error("Worker database temporarily unavailable: %s", type(error).__name__)
        stopped.wait(worker.settings.worker_interval)


if __name__ == "__main__":
    main()
