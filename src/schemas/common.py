from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceSummary(BaseModel):
    id: UUID
    title: str


class TagSummary(BaseModel):
    id: UUID
    title: str


class Pagination(BaseModel):
    limit: int
    returned: int


class FreshnessInfo(BaseModel):
    created_at: datetime | None = None
    last_synced_at: datetime | None = None
    stale: bool = False


class ResourceLinkSet(BaseModel):
    self_uri: str
    repository_uri: str | None = None
    documentation_uri: str | None = None
    routes_uri: str | None = None


class ResourceCard(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    summary: str
    canonical_url: str
    kind: Literal["repository", "documentation", "article", "resource"]
    source: str
    tags: list[str] = Field(default_factory=list)
    uris: ResourceLinkSet


class ToolEnvelope(BaseModel):
    status: Literal["success"] = "success"
    summary: str
    warnings: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
