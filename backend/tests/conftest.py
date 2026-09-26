import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.config import Settings
from backend.app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "data", local_owner="alice", worker_interval=0)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def image_bytes():
    content = io.BytesIO()
    Image.new("RGB", (40, 30), "teal").save(content, "PNG")
    return content.getvalue()


@pytest.fixture
def project(client):
    response = client.post("/api/projects", json={"name": "Test project"})
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def source(client, project, image_bytes):
    response = client.post(
        f"/api/projects/{project['id']}/images",
        files={"file": ("sample.png", image_bytes, "image/png")},
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def generation(client, project, source):
    response = client.post(
        f"/api/projects/{project['id']}/generations",
        json={"source_asset_id": source["id"]},
        headers={"Idempotency-Key": "fixture-generation"},
    )
    assert response.status_code == 202
    return response.json()
