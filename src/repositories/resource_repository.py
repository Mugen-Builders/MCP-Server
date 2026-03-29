from __future__ import annotations

from typing import Iterable
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import DocRoute, Resource, ResourceTag, Source, Tag


class ResourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _base_resource_query(self) -> Select[tuple[Resource]]:
        return (
            select(Resource)
            .options(
                selectinload(Resource.source),
                selectinload(Resource.tag_links).selectinload(ResourceTag.tag),
                selectinload(Resource.doc_routes),
                selectinload(Resource.repository_row),
            )
            .order_by(Resource.created_at.desc())
        )

    async def get_by_id(self, resource_id: UUID) -> Resource | None:
        result = await self.session.execute(
            self._base_resource_query().where(Resource.id == resource_id)
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        query: str | None = None,
        tag: str | None = None,
        source: str | None = None,
        kind: str | None = None,
        limit: int = 10,
    ) -> list[Resource]:
        stmt = self._base_resource_query().distinct()

        if query:
            needle = f"%{query.strip()}%"
            stmt = stmt.outerjoin(Resource.doc_routes).where(
                or_(
                    Resource.title.ilike(needle),
                    Resource.description.ilike(needle),
                    Resource.url.ilike(needle),
                    DocRoute.name.ilike(needle),
                    DocRoute.section.ilike(needle),
                    DocRoute.description.ilike(needle),
                )
            )

        if tag:
            stmt = stmt.join(Resource.tag_links).join(ResourceTag.tag).where(Tag.title.ilike(tag))

        if source:
            stmt = stmt.join(Resource.source).where(Source.title.ilike(source))

        if kind == "repository":
            stmt = stmt.where(Resource.is_repository.is_(True))
        elif kind == "documentation":
            stmt = stmt.where(Resource.is_documentation.is_(True))
        elif kind == "article":
            stmt = stmt.join(Resource.tag_links, isouter=True).join(ResourceTag.tag, isouter=True).where(
                func.lower(Tag.title).in_(["article", "blog", "blog post", "blog-post"])
            )

        result = await self.session.execute(stmt.limit(limit))
        return list(result.scalars().unique().all())

    async def list_by_tag(self, tag_title: str, limit: int = 10) -> list[Resource]:
        result = await self.session.execute(
            self._base_resource_query()
            .join(Resource.tag_links)
            .join(ResourceTag.tag)
            .where(Tag.title.ilike(tag_title))
            .distinct()
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def list_by_source(self, source_title: str, limit: int = 10) -> list[Resource]:
        result = await self.session.execute(
            self._base_resource_query()
            .join(Resource.source)
            .where(Source.title.ilike(source_title))
            .distinct()
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def list_doc_routes(
        self, resource_id: UUID, section: str | None = None, limit: int = 25
    ) -> tuple[Resource | None, list[DocRoute]]:
        resource = await self.get_by_id(resource_id)
        if resource is None:
            return None, []

        routes = resource.doc_routes
        if section:
            routes = [route for route in routes if route.section.lower() == section.lower()]

        routes = sorted(routes, key=lambda r: (r.section.lower(), r.name.lower()))[:limit]
        return resource, routes

    async def search_doc_routes(
        self,
        query: str,
        section: str | None = None,
        source: str | None = None,
        tag: str | None = None,
        limit: int = 10,
    ) -> list[DocRoute]:
        needle = f"%{query.strip()}%"
        stmt = (
            select(DocRoute)
            .join(DocRoute.resource)
            .options(selectinload(DocRoute.resource).selectinload(Resource.source), selectinload(DocRoute.resource).selectinload(Resource.tag_links).selectinload(ResourceTag.tag))
            .where(
                or_(
                    DocRoute.name.ilike(needle),
                    DocRoute.section.ilike(needle),
                    DocRoute.description.ilike(needle),
                    DocRoute.url.ilike(needle),
                    Resource.title.ilike(needle),
                    Resource.description.ilike(needle),
                )
            )
            .order_by(DocRoute.section.asc(), DocRoute.name.asc())
        )

        if section:
            stmt = stmt.where(DocRoute.section.ilike(section))
        if source:
            stmt = stmt.join(Resource.source).where(Source.title.ilike(source))
        if tag:
            stmt = stmt.join(Resource.tag_links).join(ResourceTag.tag).where(Tag.title.ilike(tag))

        result = await self.session.execute(stmt.limit(limit))
        return list(result.scalars().unique().all())

    async def get_doc_route(self, route_id: UUID) -> DocRoute | None:
        result = await self.session.execute(
            select(DocRoute)
            .options(selectinload(DocRoute.resource).selectinload(Resource.source), selectinload(DocRoute.resource).selectinload(Resource.tag_links).selectinload(ResourceTag.tag), selectinload(DocRoute.resource).selectinload(Resource.repository_row), selectinload(DocRoute.resource).selectinload(Resource.doc_routes))
            .where(DocRoute.id == route_id)
        )
        return result.scalar_one_or_none()

    async def list_distinct_tag_titles(self) -> list[str]:
        result = await self.session.execute(select(Tag.title).order_by(Tag.title.asc()))
        return list(result.scalars().all())

    async def list_distinct_source_titles(self) -> list[str]:
        result = await self.session.execute(select(Source.title).order_by(Source.title.asc()))
        return list(result.scalars().all())

    async def list_all_resources(self) -> list[Resource]:
        result = await self.session.execute(self._base_resource_query())
        return list(result.scalars().unique().all())

    async def count_doc_routes(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(DocRoute))
        return int(result.scalar_one())
