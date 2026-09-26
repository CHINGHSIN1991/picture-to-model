from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.providers import FakeProvider
from backend.app.worker import Worker


class FlakyProvider(FakeProvider):
    """Raises infrastructure-style errors on the first N submits, then succeeds."""

    def __init__(self, failures: int):
        super().__init__()
        self.failures = failures
        self.calls = 0

    def submit(self, source, request_key):
        self.calls += 1
        if self.calls <= self.failures:
            raise OSError("transient storage hiccup")
        return super().submit(source, request_key)


def drain(worker: Worker, limit: int = 20) -> None:
    for _ in range(limit):
        if not worker.run_once():
            break


def test_transient_errors_retry_same_stage_then_succeed(client, settings, generation):
    provider = FlakyProvider(failures=2)
    worker = Worker(replace(settings, retry_seconds=0), provider=provider)
    drain(worker)
    result = client.get(f"/api/generations/{generation['id']}").json()
    assert result["state"] == "ready", result
    assert provider.calls == 3


def test_repeated_errors_fail_after_max_attempts(client, settings, generation):
    provider = FlakyProvider(failures=100)
    worker = Worker(replace(settings, retry_seconds=0, max_attempts=3), provider=provider)
    drain(worker)
    result = client.get(f"/api/generations/{generation['id']}").json()
    assert result["state"] == "failed"
    assert result["error"]["code"] == "generation_failed"
    # queued → submitting is one attempt; the remaining budget is spent on submit.
    assert provider.calls == 2


def test_generation_exposes_source_and_new_key_can_retry_after_failure(
    client, settings, project, source, generation
):
    worker = Worker(
        replace(settings, retry_seconds=0, max_attempts=1), provider=FlakyProvider(failures=100)
    )
    drain(worker)
    failed = client.get(f"/api/generations/{generation['id']}").json()
    assert failed["state"] == "failed"
    assert failed["source_asset_id"] == source["id"]
    retry = client.post(
        f"/api/projects/{project['id']}/generations",
        json={"source_asset_id": source["id"]},
        headers={"Idempotency-Key": "second-attempt"},
    )
    assert retry.status_code == 202
    assert retry.json()["id"] != generation["id"]
    assert retry.json()["state"] == "queued"


def test_health_and_persistence(client, settings, project, source):
    assert client.get("/api/health").json() == {"status": "ok", "provider": "fake", "mode": "local"}
    with TestClient(create_app(settings)) as restarted:
        result = restarted.get(f"/api/projects/{project['id']}")
        assert result.json()["source_asset_id"] == source["id"]
        assert restarted.get("/api/projects").json()["items"][0]["id"] == project["id"]
        assert restarted.get(source["url"]).status_code == 200


def test_local_owner_is_server_controlled_and_all_assets_are_isolated(
    client, settings, project, source, generation
):
    worker = Worker(settings)
    for _ in range(5):
        assert worker.run_once()
    ready = client.get(f"/api/generations/{generation['id']}").json()
    version = client.get(f"/api/model-versions/{ready['model_version_id']}").json()
    # A malicious header never changes the owner chosen from server settings.
    assert client.get("/api/projects", headers={"X-Owner-ID": "mallory"}).json()["items"]
    with TestClient(create_app(replace(settings, local_owner="bob"))) as outsider:
        headers = {"X-Owner-ID": "alice"}
        assert outsider.get("/api/projects", headers=headers).json() == {"items": []}
        for path in [
            f"/api/projects/{project['id']}",
            source["url"],
            f"/api/generations/{generation['id']}",
            f"/api/model-versions/{ready['model_version_id']}",
            version["asset_url"],
        ]:
            response = outsider.get(path, headers=headers)
            assert response.status_code == 404, path
        upload = outsider.post(
            f"/api/projects/{project['id']}/images",
            headers=headers,
            files={"file": ("x.png", b"bad", "image/png")},
        )
        assert upload.status_code == 404
        response = outsider.post(
            f"/api/projects/{project['id']}/generations",
            json={"source_asset_id": source["id"]},
            headers={**headers, "Idempotency-Key": "stolen"},
        )
        assert response.status_code == 404


def test_source_must_belong_to_requested_project(client, source):
    other = client.post("/api/projects", json={"name": "Another"}).json()
    response = client.post(
        f"/api/projects/{other['id']}/generations",
        json={"source_asset_id": source["id"]},
        headers={"Idempotency-Key": "wrong-source"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "source_not_found"


def test_parallel_idempotency_creates_exactly_one_job(client, project, source, settings):
    def submit(_):
        response = client.post(
            f"/api/projects/{project['id']}/generations",
            json={"source_asset_id": source["id"]},
            headers={"Idempotency-Key": "same-action"},
        )
        assert response.status_code == 202
        return response.json()["id"]

    with ThreadPoolExecutor(max_workers=6) as pool:
        identifiers = list(pool.map(submit, range(12)))
    assert len(set(identifiers)) == 1
    with client.app.state.database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
    with TestClient(create_app(settings)) as restarted:
        response = restarted.post(
            f"/api/projects/{project['id']}/generations",
            json={"source_asset_id": source["id"]},
            headers={"Idempotency-Key": "same-action"},
        )
        assert response.json()["id"] == identifiers[0]


def test_idempotency_conflict_for_changed_source(client, project, source, generation, image_bytes):
    replacement = client.post(
        f"/api/projects/{project['id']}/images",
        files={"file": ("another.png", image_bytes, "image/png")},
    ).json()
    response = client.post(
        f"/api/projects/{project['id']}/generations",
        json={"source_asset_id": replacement["id"]},
        headers={"Idempotency-Key": "fixture-generation"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "idempotency_conflict"


def test_structured_validation_and_not_found(client):
    for response in [
        client.post("/api/projects", json={"name": "  "}),
        client.get("/api/projects/does-not-exist"),
        client.get("/unknown"),
    ]:
        payload = response.json()
        assert set(payload) == {"code", "message", "retryable", "request_id"}
        assert payload["request_id"] == response.headers["x-request-id"]
        assert payload["retryable"] is False


def test_origin_and_host_restrictions(client, settings):
    assert (
        client.post(
            "/api/projects", json={"name": "Bad origin"}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400
    custom = replace(settings, web_origin="http://127.0.0.1:15173")
    with TestClient(create_app(custom)) as overridden:
        assert (
            overridden.post(
                "/api/projects", json={"name": "Custom port"}, headers={"Origin": custom.web_origin}
            ).status_code
            == 201
        )


def test_missing_idempotency_key_rejected(client, project, source):
    response = client.post(
        f"/api/projects/{project['id']}/generations", json={"source_asset_id": source["id"]}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"
