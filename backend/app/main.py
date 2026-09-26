import hashlib
import json
import logging
import sqlite3
import time
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, Header, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from .config import Settings
from .db import Database, timestamp
from .errors import AppError
from .images import MAX_UPLOAD_BYTES, sanitize_image
from .schemas import (
    Asset,
    Generation,
    GenerationCreate,
    ModelVersion,
    Project,
    ProjectCreate,
    ProjectDetail,
    ProjectList,
)
from .storage import LocalStorage

logger = logging.getLogger(__name__)
LOCAL_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
}


def generation_payload(row: sqlite3.Row) -> dict:
    return {
        **dict(row),
        "error": {"code": row["error_code"], "message": row["error_message"]}
        if row["error_code"]
        else None,
    }


def owned_project(connection: sqlite3.Connection, project_id: str, owner: str) -> sqlite3.Row:
    project = connection.execute(
        "SELECT * FROM projects WHERE id = ? AND owner_id = ?", (project_id, owner)
    ).fetchone()
    if project is None:
        raise AppError("not_found", "找不到專案。", 404)
    return project


UPLOAD_BODY_LIMIT = MAX_UPLOAD_BYTES + 64 * 1024  # Image plus bounded multipart overhead.


class LimitUploadBody:
    """Single ASGI-level cap for both Content-Length and chunked uploads."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].endswith("/images"):
            await self.app(scope, receive, send)
            return
        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > UPLOAD_BODY_LIMIT:
                    # FastAPI preserves HTTPException from multipart parsing,
                    # while wrapping arbitrary errors into a generic HTTP 400.
                    raise HTTPException(status_code=413)
            return message

        await self.app(scope, limited_receive, send)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    database = Database(settings.database_path)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        await run_in_threadpool(database.initialize)
        application.state.storage = LocalStorage(settings.assets_dir)
        yield

    application = FastAPI(title="Picture to Model — local fixture API", lifespan=lifespan)
    application.state.database = database
    application.state.settings = settings
    application.add_middleware(LimitUploadBody)

    def error_response(request: Request, error: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status,
            content={
                "code": error.code,
                "message": error.message,
                "retryable": error.retryable,
                "request_id": getattr(request.state, "request_id", uuid4().hex),
            },
            headers={
                "X-Request-ID": getattr(request.state, "request_id", uuid4().hex),
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = uuid4().hex
        # This fixed local owner is not authentication. Reject foreign browser origins
        # and Host headers; the documented server command also binds loopback only.
        host = request.url.hostname
        if host not in {"localhost", "127.0.0.1", "::1", "testserver"}:
            response = error_response(request, AppError("invalid_host", "僅支援本機連線。", 400))
        elif request.headers.get("origin") not in LOCAL_ORIGINS | {None, settings.web_origin}:
            response = error_response(
                request, AppError("origin_not_allowed", "請從本機開發介面操作。", 403)
            )
        else:
            response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        return response

    @application.exception_handler(AppError)
    async def handle_app_error(request: Request, error: AppError):
        return error_response(request, error)

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, error: RequestValidationError):
        return error_response(
            request, AppError("invalid_request", "請檢查必填欄位與輸入格式。", 422)
        )

    @application.exception_handler(HTTPException)
    async def handle_http_error(request: Request, error: HTTPException):
        if error.status_code == 413:
            return error_response(
                request, AppError("image_too_large", "圖片不可超過 10 MiB。", 413)
            )
        code = "not_found" if error.status_code == 404 else "invalid_request"
        return error_response(request, AppError(code, "請求無法處理。", error.status_code))

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception):
        logger.error(
            "Internal failure request_id=%s type=%s", request.state.request_id, type(error).__name__
        )
        return error_response(
            request, AppError("internal_error", "系統暫時無法處理請求。", 500, True)
        )

    @application.get("/api/health")
    def health():
        return {"status": "ok", "provider": "fake", "mode": "local"}

    @application.post("/api/projects", response_model=Project, status_code=201)
    def create_project(body: ProjectCreate):
        project = {
            "id": str(uuid4()),
            "name": body.name,
            "created_at": timestamp(),
            "source_asset_id": None,
        }
        with database.transaction() as connection:
            connection.execute(
                "INSERT INTO projects (id, owner_id, name, created_at) VALUES (?, ?, ?, ?)",
                (project["id"], settings.local_owner, project["name"], project["created_at"]),
            )
        return project

    @application.get("/api/projects", response_model=ProjectList)
    def list_projects():
        with database.connect() as connection:
            projects = connection.execute(
                "SELECT * FROM projects WHERE owner_id = ? ORDER BY created_at DESC",
                (settings.local_owner,),
            ).fetchall()
        return {"items": [dict(row) for row in projects]}

    @application.get("/api/projects/{project_id}", response_model=ProjectDetail)
    def get_project(project_id: str):
        with database.connect() as connection:
            project = owned_project(connection, project_id, settings.local_owner)
            generations = connection.execute(
                "SELECT * FROM generations WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        return {**dict(project), "generations": [generation_payload(row) for row in generations]}

    @application.post("/api/projects/{project_id}/images", response_model=Asset, status_code=201)
    def upload_image(project_id: str, file: UploadFile, request: Request):
        with database.connect() as connection:
            owned_project(connection, project_id, settings.local_owner)
        try:
            image = sanitize_image(
                file.file.read(MAX_UPLOAD_BYTES + 1), file.filename or "", file.content_type
            )
        finally:
            file.file.close()
        asset_id = str(uuid4())
        key = f"{asset_id.replace('-', '')}.{image.extension}"
        storage = request.app.state.storage
        storage.write(key, image.content)
        try:
            with database.transaction() as connection:
                owned_project(connection, project_id, settings.local_owner)
                connection.execute(
                    "INSERT INTO assets VALUES (?, ?, 'image', ?, ?, ?, ?, ?)",
                    (
                        asset_id,
                        project_id,
                        key,
                        hashlib.sha256(image.content).hexdigest(),
                        image.mime,
                        len(image.content),
                        timestamp(),
                    ),
                )
                connection.execute(
                    "UPDATE projects SET source_asset_id = ? WHERE id = ?", (asset_id, project_id)
                )
        except BaseException:
            storage.delete(key)
            raise
        return {
            "id": asset_id,
            "url": f"/api/assets/{asset_id}/content",
            "mime": image.mime,
            "bytes": len(image.content),
        }

    @application.post(
        "/api/projects/{project_id}/generations", response_model=Generation, status_code=202
    )
    def create_generation(
        project_id: str,
        body: GenerationCreate,
        idempotency_key: Annotated[str, Header(min_length=1, max_length=128)],
    ):
        with database.transaction() as connection:
            owned_project(connection, project_id, settings.local_owner)
            source = connection.execute(
                "SELECT id FROM assets WHERE id = ? AND project_id = ? AND kind = 'image'",
                (body.source_asset_id, project_id),
            ).fetchone()
            if source is None:
                raise AppError("source_not_found", "找不到這個專案的來源圖片。", 404)
            previous = connection.execute(
                "SELECT * FROM generations WHERE owner_id = ? AND idempotency_key = ?",
                (settings.local_owner, idempotency_key),
            ).fetchone()
            if previous:
                same_target = (
                    previous["project_id"] == project_id
                    and previous["source_asset_id"] == source["id"]
                )
                if not same_target:
                    raise AppError(
                        "idempotency_conflict", "此請求識別碼已用於不同的生成內容。", 409
                    )
                return generation_payload(previous)
            generation_id = str(uuid4())
            now = timestamp()
            connection.execute(
                "INSERT INTO generations (id, project_id, owner_id, source_asset_id, provider, "
                "provider_model, state, idempotency_key, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 'fake', 'fixture-v1', 'queued', ?, ?, ?)",
                (
                    generation_id,
                    project_id,
                    settings.local_owner,
                    source["id"],
                    idempotency_key,
                    now,
                    now,
                ),
            )
            connection.execute(
                "INSERT INTO jobs (id, generation_id, next_run_at, created_at) VALUES (?, ?, ?, ?)",
                (str(uuid4()), generation_id, time.time(), now),
            )
            generation = connection.execute(
                "SELECT * FROM generations WHERE id = ?", (generation_id,)
            ).fetchone()
        return generation_payload(generation)

    @application.get("/api/generations/{generation_id}", response_model=Generation)
    def get_generation(generation_id: str):
        with database.connect() as connection:
            generation = connection.execute(
                "SELECT g.* FROM generations g JOIN projects p ON p.id = g.project_id "
                "WHERE g.id = ? AND p.owner_id = ?",
                (generation_id, settings.local_owner),
            ).fetchone()
        if generation is None:
            raise AppError("not_found", "找不到生成任務。", 404)
        return generation_payload(generation)

    @application.get("/api/model-versions/{version_id}", response_model=ModelVersion)
    def get_model_version(version_id: str):
        with database.connect() as connection:
            version = connection.execute(
                "SELECT v.*, g.provider FROM model_versions v "
                "JOIN generations g ON g.id = v.generation_id "
                "JOIN projects p ON p.id = g.project_id WHERE v.id = ? AND p.owner_id = ?",
                (version_id, settings.local_owner),
            ).fetchone()
        if version is None:
            raise AppError("not_found", "找不到模型版本。", 404)
        return {
            "id": version["id"],
            "provider": version["provider"],
            "asset_url": f"/api/assets/{version['original_asset_id']}/content",
            "metrics": json.loads(version["metrics"]),
        }

    @application.get("/api/assets/{asset_id}/content")
    def get_asset_content(asset_id: str, request: Request):
        with database.connect() as connection:
            asset = connection.execute(
                "SELECT a.* FROM assets a JOIN projects p ON p.id = a.project_id "
                "WHERE a.id = ? AND p.owner_id = ?",
                (asset_id, settings.local_owner),
            ).fetchone()
        if asset is None:
            raise AppError("not_found", "找不到檔案。", 404)
        path = request.app.state.storage.path(asset["storage_key"])
        if not path.is_file():
            raise AppError("asset_unavailable", "檔案已不存在，請重新上傳或生成。", 404)
        return FileResponse(
            path, media_type=asset["mime"], filename=path.name, content_disposition_type="inline"
        )

    return application


app = create_app()
