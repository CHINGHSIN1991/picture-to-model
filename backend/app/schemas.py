from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=100)


class GenerationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_asset_id: str = Field(min_length=1, max_length=64)


class Project(BaseModel):
    id: str
    name: str
    created_at: str
    source_asset_id: str | None


class ProjectList(BaseModel):
    items: list[Project]


class GenerationError(BaseModel):
    code: str
    message: str


class Generation(BaseModel):
    id: str
    project_id: str
    source_asset_id: str
    state: Literal[
        "queued", "submitting", "generating", "downloading", "validating", "ready", "failed"
    ]
    provider: Literal["fake"]
    created_at: str
    model_version_id: str | None
    error: GenerationError | None


class ProjectDetail(Project):
    generations: list[Generation]


class Asset(BaseModel):
    id: str
    url: str
    mime: str
    bytes: int


class ModelMetrics(BaseModel):
    triangles: int
    bytes: int


class ModelVersion(BaseModel):
    id: str
    asset_url: str
    provider: Literal["fake"]
    metrics: ModelMetrics
