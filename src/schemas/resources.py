from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.common import FreshnessInfo, ResourceCard, ResourceLinkSet, SourceSummary, TagSummary


class DocRouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    section: str
    url: str
    description: str | None = None
    created_at: datetime | None = None
    uri: str


class ResourceDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    canonical_url: str
    kind: Literal["repository", "documentation", "article", "resource"]
    source: SourceSummary
    tags: list[TagSummary] = Field(default_factory=list)
    freshness: FreshnessInfo
    uris: ResourceLinkSet
    route_count: int = 0
    routes: list[DocRouteOut] = Field(default_factory=list)


class SearchResourcesResult(BaseModel):
    cards: list[ResourceCard]


class ListDocRoutesResult(BaseModel):
    resource_id: UUID
    resource_title: str
    routes: list[DocRouteOut]


class RepositoryStatus(BaseModel):
    resource_id: UUID
    repository_row_id: UUID
    title: str
    canonical_url: str
    source: str
    tags: list[str] = Field(default_factory=list)
    last_synced_at: datetime | None = None
    uri: str
