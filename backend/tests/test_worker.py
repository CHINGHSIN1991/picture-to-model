import time
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.providers import FakeProvider, ProviderStatus
from backend.app.worker import Worker


class Clock:
    def __init__(self):
        self.now = time.time() + 1

    def __call__(self):
        return self.now


def drain(worker, limit=40):
    for _ in range(limit):
        if not worker.run_once():
            return
    pytest.fail("Worker did not finish within the expected number of stages")


def generation_row(worker, generation_id):
    with worker.database.connect() as connection:
        return connection.execute(
            "SELECT * FROM generations WHERE id = ?", (generation_id,)
        ).fetchone()


def assert_single_completed_model(worker, generation_id):
    with worker.database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM model_versions").fetchone()[0] == 1
        assert (
            connection.execute("SELECT COUNT(*) FROM assets WHERE kind = 'model'").fetchone()[0]
            == 1
        )
        job = connection.execute(
            "SELECT * FROM jobs WHERE generation_id = ?", (generation_id,)
        ).fetchone()
        assert job["status"] == "completed"
        assert job["lease_token"] is None
        assert job["lease_expires_at"] is None


def test_resume_after_provider_accepts_submit_before_database_commit(settings, generation):
    accepted_tasks = []

    class RecordingProvider(FakeProvider):
        def submit(self, source, request_key):
            task = super().submit(source, request_key)
            accepted_tasks.append(task)
            return task

    class CrashingWorker(Worker):
        def _advance(self, claim, state, **fields):
            if state == "generating":
                raise SystemExit("Simulated process death after submit")
            return super()._advance(claim, state, **fields)

    clock = Clock()
    original = CrashingWorker(settings, RecordingProvider(), clock)
    assert original.run_once()  # Persist submitting before the external side effect.
    with pytest.raises(SystemExit):
        original.run_once()
    interrupted = generation_row(original, generation["id"])
    assert interrupted["state"] == "submitting"
    assert interrupted["provider_task_id"] is None
    assert len(accepted_tasks) == 1

    # A new worker/provider instance observes the durable lease, then reuses the
    # generation request key when the abandoned lease expires.
    restarted = Worker(settings, RecordingProvider(), clock)
    assert restarted.claim() is None
    clock.now += settings.lease_seconds + 1
    drain(restarted)
    ready = generation_row(restarted, generation["id"])
    assert ready["state"] == "ready"
    assert accepted_tasks == [ready["provider_task_id"], ready["provider_task_id"]]
    assert_single_completed_model(restarted, generation["id"])


def test_expired_claim_cannot_advance_or_release_replacement_lease(settings, generation):
    clock = Clock()
    original, replacement = Worker(settings, clock=clock), Worker(settings, clock=clock)
    stale = original.claim()
    assert stale is not None
    assert replacement.claim() is None
    clock.now += settings.lease_seconds + 1
    current = replacement.claim()
    assert current is not None
    assert current.token != stale.token
    assert original._advance(stale, "failed", error_code="stale") is False
    original._retry_later(stale)
    original.process(stale)
    with replacement.database.connect() as connection:
        job = connection.execute("SELECT * FROM jobs").fetchone()
        assert job["lease_token"] == current.token
    assert generation_row(replacement, generation["id"])["state"] == "queued"
    replacement.process(current)
    drain(replacement)
    assert_single_completed_model(replacement, generation["id"])


def test_stale_download_cannot_overwrite_replacement_result(settings, generation):
    clock = Clock()
    replacement = Worker(settings, clock=clock)

    class SlowProvider(FakeProvider):
        def fetch_result(self, task_id):
            # Another worker finishes while this slow request is still in flight.
            clock.now += settings.lease_seconds + 1
            drain(replacement)
            return b"stale bytes that must never replace the committed model"

    original = Worker(settings, SlowProvider(), clock)
    for _ in range(3):
        assert original.run_once()
    assert generation_row(original, generation["id"])["state"] == "downloading"
    assert original.run_once()
    ready = generation_row(replacement, generation["id"])
    assert ready["state"] == "ready"
    committed = replacement.storage.path(ready["result_storage_key"])
    assert committed.read_bytes() == FakeProvider().fetch_result(ready["provider_task_id"])
    assert list(settings.assets_dir.glob("*.glb")) == [committed]
    assert_single_completed_model(replacement, generation["id"])


def test_expired_validation_and_restart_do_not_duplicate_ready_model(settings, generation):
    clock = Clock()
    original = Worker(settings, clock=clock)
    for _ in range(4):
        assert original.run_once()
    stale = original.claim()
    assert stale is not None
    snapshot = generation_row(original, generation["id"])
    assert snapshot["state"] == "validating"
    clock.now += settings.lease_seconds + 1
    replacement = Worker(settings, clock=clock)
    drain(replacement)
    ready = generation_row(replacement, generation["id"])
    original._finish(stale, snapshot, b"stale", {})
    original.process(stale)
    assert (
        generation_row(original, generation["id"])["model_version_id"] == ready["model_version_id"]
    )
    assert Worker(settings, clock=clock).run_once() is False
    assert_single_completed_model(replacement, generation["id"])
    with TestClient(create_app(settings)) as restarted_api:
        persisted = restarted_api.get(f"/api/generations/{generation['id']}").json()
        assert persisted["state"] == "ready"
        assert persisted["model_version_id"] == ready["model_version_id"]
        version = restarted_api.get(f"/api/model-versions/{ready['model_version_id']}").json()
        assert restarted_api.get(version["asset_url"]).content.startswith(b"glTF")


def test_successful_stages_and_pending_polls_reset_failure_budget(settings, generation):
    class RetryingProvider(FakeProvider):
        def __init__(self):
            super().__init__()
            self.submits = self.polls = self.downloads = 0

        def submit(self, source, request_key):
            self.submits += 1
            if self.submits < 3:
                raise OSError("Transient submit error")
            return super().submit(source, request_key)

        def get_status(self, task_id):
            self.polls += 1
            if self.polls < 3:
                raise OSError("Transient polling error")
            return ProviderStatus("pending" if self.polls < 8 else "succeeded")

        def fetch_result(self, task_id):
            self.downloads += 1
            if self.downloads < 3:
                raise OSError("Transient download error")
            return super().fetch_result(task_id)

    provider = RetryingProvider()
    worker = Worker(replace(settings, max_attempts=3, retry_seconds=0), provider)
    drain(worker)
    assert generation_row(worker, generation["id"])["state"] == "ready"
    assert (provider.submits, provider.polls, provider.downloads) == (3, 8, 3)
    assert_single_completed_model(worker, generation["id"])


def test_retry_backoff_is_durable_across_worker_restart(settings, generation):
    class UnavailableProvider(FakeProvider):
        def submit(self, source, request_key):
            raise OSError("Temporarily unavailable")

    clock = Clock()
    worker = Worker(settings, UnavailableProvider(), clock)
    assert worker.run_once()
    assert worker.run_once()
    restarted = Worker(settings, UnavailableProvider(), clock)
    assert restarted.claim() is None
    clock.now += settings.retry_seconds
    assert restarted.run_once()
    clock.now += settings.retry_seconds
    assert restarted.claim() is None  # Second failure doubles the persisted delay.
    clock.now += settings.retry_seconds
    recovered = Worker(settings, clock=clock)
    drain(recovered)
    assert generation_row(recovered, generation["id"])["state"] == "ready"


def test_worker_does_not_claim_another_local_owners_jobs(settings, generation):
    outsider = Worker(replace(settings, local_owner="bob"))
    assert outsider.claim() is None
    assert generation_row(outsider, generation["id"])["state"] == "queued"
