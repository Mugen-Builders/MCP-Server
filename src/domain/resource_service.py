from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.formatters.resource_formatter import format_card, format_detail, format_doc_route, format_repository_status
from src.repositories.resource_repository import ResourceRepository
from src.schemas.resources import ListDocRoutesResult, RepositoryStatus, ResourceDetail, SearchResourcesResult


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

    async def get_tag_catalog(self) -> list[str]:
        return await self.repo.list_distinct_tag_titles()

    async def get_source_catalog(self) -> list[str]:
        return await self.repo.list_distinct_source_titles()

    async def get_knowledge_base_summary(self) -> dict:
        resources = await self.repo.list_all_resources()
        repo_count = sum(1 for r in resources if r.is_repository)
        doc_count = sum(1 for r in resources if r.is_documentation)
        other_count = len(resources) - repo_count - doc_count
        doc_route_count = await self.repo.count_doc_routes()

        return {
            "summary": {
                "total_resources": len(resources),
                "repositories": repo_count,
                "documentation": doc_count,
                "articles_and_other": other_count,
                "total_doc_routes": doc_route_count,
            },
            "tags": await self.get_tag_catalog(),
            "sources": await self.get_source_catalog(),
        }
