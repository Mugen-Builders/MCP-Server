from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.formatters.resource_formatter import format_article_content, format_card, format_detail, format_doc_route, format_repository_status, format_skill_content
from src.repositories.resource_repository import ResourceRepository
from src.schemas.resources import ListDocRoutesResult, RepositoryStatus, ResourceDetail, SearchResourcesResult

_TAXONOMY_TTL = timedelta(minutes=10)
_taxonomy_cache: dict | None = None
_taxonomy_cache_ts: datetime | None = None
_counts_cache: dict | None = None
_counts_cache_ts: datetime | None = None


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class NotFoundError(ValueError):
    pass


class ResourceService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ResourceRepository(session)

    async def search_resources(
        self,
        query: str | None = None,
        tag: str | None = None,
        source: str | None = None,
        kind: str | None = None,
        limit: int = 10,
    ) -> SearchResourcesResult:
        rows = await self.repo.search(query=query, tag=tag, source=source, kind=kind, limit=limit)
        return SearchResourcesResult(cards=[format_card(row) for row in rows])

    async def get_resource_details(self, resource_id: UUID, include_routes: bool = True) -> ResourceDetail:
        row = await self.repo.get_by_id(resource_id)
        if row is None:
            raise NotFoundError(f"Resource {resource_id} was not found")
        return format_detail(row, include_routes=include_routes)

    async def list_doc_routes(self, resource_id: UUID, section: str | None = None, limit: int = 25) -> ListDocRoutesResult:
        resource, routes = await self.repo.list_doc_routes(resource_id=resource_id, section=section, limit=limit)
        if resource is None:
            raise NotFoundError(f"Resource {resource_id} was not found")
        return ListDocRoutesResult(
            resource_id=resource.id,
            resource_title=resource.title,
            routes=[format_doc_route(route) for route in routes],
        )

    async def search_doc_routes(
        self, query: str, section: str | None = None, source: str | None = None, tag: str | None = None, limit: int = 10
    ) -> list[dict]:
        rows = await self.repo.search_doc_routes(query=query, section=section, source=source, tag=tag, limit=limit)
        payload: list[dict] = []
        for route in rows:
            payload.append(
                {
                    "route": format_doc_route(route).model_dump(mode="json"),
                    "resource": format_card(route.resource).model_dump(mode="json"),
                }
            )
        return payload

    async def list_resources_by_tag(self, tag_title: str, limit: int = 10) -> SearchResourcesResult:
        rows = await self.repo.list_by_tag(tag_title=tag_title, limit=limit)
        return SearchResourcesResult(cards=[format_card(row) for row in rows])

    async def list_resources_by_source(self, source_title: str, limit: int = 10) -> SearchResourcesResult:
        rows = await self.repo.list_by_source(source_title=source_title, limit=limit)
        return SearchResourcesResult(cards=[format_card(row) for row in rows])

    async def get_repository_status(self, resource_id: UUID) -> RepositoryStatus:
        row = await self.repo.get_by_id(resource_id)
        if row is None:
            raise NotFoundError(f"Resource {resource_id} was not found")
        if row.repository_row is None:
            raise NotFoundError(f"Resource {resource_id} is not a repository")
        return format_repository_status(row)

    async def get_doc_route_detail(self, route_id: UUID) -> dict:
        row = await self.repo.get_doc_route(route_id)
        if row is None:
            raise NotFoundError(f"Doc route {route_id} was not found")
        return {
            "route": format_doc_route(row).model_dump(mode="json"),
            "resource": format_detail(row.resource, include_routes=False).model_dump(mode="json"),
        }

    async def get_debugging_context(self, query: str, prefer_official_only: bool = False, limit: int = 8) -> dict:
        source_filter = "core contributors" if prefer_official_only else None
        resource_hits = await self.search_resources(query=query, source=source_filter, limit=limit)
        route_hits = await self.search_doc_routes(query=query, source=source_filter, limit=limit)
        return {
            "query": query,
            "prefer_official_only": prefer_official_only,
            "resources": resource_hits.model_dump(mode="json")["cards"],
            "doc_routes": route_hits,
        }

    async def list_doc_route_sections(self, resource_id: UUID) -> list[str]:
        row = await self.repo.get_by_id(resource_id)
        if row is None:
            raise NotFoundError(f"Resource {resource_id} was not found")
        return await self.repo.list_distinct_route_sections(resource_id)

    async def get_tag_catalog(self) -> list[str]:
        global _taxonomy_cache, _taxonomy_cache_ts
        now = _utcnow()
        if _taxonomy_cache is None or _taxonomy_cache_ts is None or (now - _taxonomy_cache_ts) > _TAXONOMY_TTL:
            tags = await self.repo.list_distinct_tag_titles()
            sources = await self.repo.list_distinct_source_titles()
            _taxonomy_cache = {"tags": tags, "sources": sources}
            _taxonomy_cache_ts = now
        return _taxonomy_cache["tags"]

    async def get_source_catalog(self) -> list[str]:
        global _taxonomy_cache, _taxonomy_cache_ts
        now = _utcnow()
        if _taxonomy_cache is None or _taxonomy_cache_ts is None or (now - _taxonomy_cache_ts) > _TAXONOMY_TTL:
            tags = await self.repo.list_distinct_tag_titles()
            sources = await self.repo.list_distinct_source_titles()
            _taxonomy_cache = {"tags": tags, "sources": sources}
            _taxonomy_cache_ts = now
        return _taxonomy_cache["sources"]

    async def get_knowledge_base_summary(self) -> dict:
        global _counts_cache, _counts_cache_ts
        now = _utcnow()
        if _counts_cache is None or _counts_cache_ts is None or (now - _counts_cache_ts) > _TAXONOMY_TTL:
            counts = await self.repo.count_resources_by_type()
            doc_route_count = await self.repo.count_doc_routes()
            _counts_cache = {
                "total_resources": counts["total"],
                "repositories": counts["repositories"],
                "documentation": counts["documentation"],
                "articles": counts["articles"],
                "skills": counts["skills"],
                "other": counts["other"],
                "total_doc_routes": doc_route_count,
            }
            _counts_cache_ts = now

        return {
            "summary": _counts_cache,
        }

    async def list_articles(
        self, tag: str | None = None, source: str | None = None, limit: int = 20
    ) -> SearchResourcesResult:
        rows = await self.repo.list_articles(tag=tag, source=source, limit=limit)
        return SearchResourcesResult(cards=[format_card(row) for row in rows])

    async def get_article(self, resource_id: UUID) -> dict:
        row = await self.repo.get_by_id(resource_id)
        if row is None:
            raise NotFoundError(f"Resource {resource_id} was not found")
        if not row.is_article or row.article_row is None:
            raise NotFoundError(f"Resource {resource_id} is not an article")
        content = format_article_content(row)
        return {
            "resource": format_card(row).model_dump(mode="json"),
            "article_content": content.model_dump(mode="json") if content else None,
        }

    async def list_skills(
        self, tag: str | None = None, source: str | None = None, limit: int = 50
    ) -> list[dict]:
        rows = await self.repo.list_skills(tag=tag, source=source, limit=limit)
        return [
            {
                "resource_id": str(row.id),
                "title": row.title,
                "description": row.description,
                "source": row.source.title,
                "tags": sorted([link.tag.title for link in row.tag_links]),
                "last_updated_at": row.skill_row.last_updated_at.isoformat() if row.skill_row and row.skill_row.last_updated_at else None,
                "body_available": True,
                "hint": f"Call get_skill with resource_id='{row.id}' to retrieve the full skill body.",
            }
            for row in rows
        ]

    async def get_skill(self, resource_id: UUID) -> dict:
        row = await self.repo.get_by_id(resource_id)
        if row is None:
            raise NotFoundError(f"Resource {resource_id} was not found")
        if not row.is_skill or row.skill_row is None:
            raise NotFoundError(f"Resource {resource_id} is not a skill")
        content = format_skill_content(row)
        return {
            "resource_id": str(row.id),
            "title": row.title,
            "description": row.description,
            "source": row.source.title,
            "tags": sorted([link.tag.title for link in row.tag_links]),
            "skill_content": content.model_dump(mode="json") if content else None,
        }
