from __future__ import annotations

from typing import Iterable
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import Article, DocRoute, Resource, ResourceTag, Skill, Source, Tag


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
                selectinload(Resource.article_row),
                selectinload(Resource.skill_row),
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
            q = query.strip()
            # Attempt PostgreSQL full-text search using websearch_to_tsquery for natural-language queries.
            # Falls back to ILIKE if the tsquery syntax is invalid or unsupported.
            try:
                from sqlalchemy import cast as sa_cast, text
                from sqlalchemy.dialects.postgresql import TSVECTOR
                ts_vector = func.to_tsvector(
                    "english",
                    func.coalesce(Resource.title, "") + " " + func.coalesce(Resource.description, ""),
                )
                ts_query = func.websearch_to_tsquery("english", q)
                fts_filter = ts_vector.op("@@")(ts_query)
                stmt = stmt.where(fts_filter)
            except Exception:
                # Fallback to ILIKE for non-PostgreSQL or unexpected errors
                needle = f"%{q}%"
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
        resource_result = await self.session.execute(
            select(Resource)
            .options(
                selectinload(Resource.source),
                selectinload(Resource.tag_links).selectinload(ResourceTag.tag),
            )
            .where(Resource.id == resource_id)
        )
        resource = resource_result.scalar_one_or_none()
        if resource is None:
            return None, []

        route_stmt = (
            select(DocRoute)
            .where(DocRoute.resource_id == resource_id)
            .order_by(DocRoute.section.asc(), DocRoute.name.asc())
            .limit(limit)
        )
        if section:
            route_stmt = route_stmt.where(DocRoute.section.ilike(section))

        routes_result = await self.session.execute(route_stmt)
        return resource, list(routes_result.scalars().all())

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
            .options(
                selectinload(DocRoute.resource).selectinload(Resource.source),
                selectinload(DocRoute.resource).selectinload(Resource.tag_links).selectinload(ResourceTag.tag),
                selectinload(DocRoute.resource).selectinload(Resource.repository_row),
                # Removed: selectinload(Resource.doc_routes) — sibling routes are never returned here
            )
            .where(DocRoute.id == route_id)
        )
        return result.scalar_one_or_none()

    async def list_distinct_route_sections(self, resource_id: UUID) -> list[str]:
        """Return all distinct section names for a given documentation resource."""
        result = await self.session.execute(
            select(DocRoute.section)
            .where(DocRoute.resource_id == resource_id)
            .distinct()
            .order_by(DocRoute.section.asc())
        )
        return [row for row in result.scalars().all() if row]

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

    async def count_resources_by_type(self) -> dict[str, int]:
        """Return resource counts by type using targeted COUNT queries (no eager loading)."""
        total_result = await self.session.execute(select(func.count()).select_from(Resource))
        repo_result = await self.session.execute(
            select(func.count()).select_from(Resource).where(Resource.is_repository.is_(True))
        )
        doc_result = await self.session.execute(
            select(func.count()).select_from(Resource).where(Resource.is_documentation.is_(True))
        )
        article_result = await self.session.execute(
            select(func.count()).select_from(Resource).where(Resource.is_article.is_(True))
        )
        skill_result = await self.session.execute(
            select(func.count()).select_from(Resource).where(Resource.is_skill.is_(True))
        )
        total = int(total_result.scalar_one())
        repos = int(repo_result.scalar_one())
        docs = int(doc_result.scalar_one())
        articles = int(article_result.scalar_one())
        skills = int(skill_result.scalar_one())
        other = total - repos - docs - articles - skills
        return {
            "total": total,
            "repositories": repos,
            "documentation": docs,
            "articles": articles,
            "skills": skills,
            "other": other,
        }

    async def list_articles(
        self, tag: str | None = None, source: str | None = None, limit: int = 20
    ) -> list[Resource]:
        """Return resources where is_article=True, eager-loading the article_row body."""
        stmt = self._base_resource_query().where(Resource.is_article.is_(True))
        if tag:
            stmt = stmt.join(Resource.tag_links).join(ResourceTag.tag).where(Tag.title.ilike(tag))
        if source:
            stmt = stmt.join(Resource.source).where(Source.title.ilike(source))
        result = await self.session.execute(stmt.distinct().limit(limit))
        return list(result.scalars().unique().all())

    async def list_skills(
        self, tag: str | None = None, source: str | None = None, limit: int = 50
    ) -> list[Resource]:
        """Return resources where is_skill=True, eager-loading the skill_row body."""
        stmt = self._base_resource_query().where(Resource.is_skill.is_(True))
        if tag:
            stmt = stmt.join(Resource.tag_links).join(ResourceTag.tag).where(Tag.title.ilike(tag))
        if source:
            stmt = stmt.join(Resource.source).where(Source.title.ilike(source))
        result = await self.session.execute(stmt.distinct().limit(limit))
        return list(result.scalars().unique().all())

    async def search_skills(
        self, query: str, tag: str | None = None, source: str | None = None, limit: int = 10
    ) -> list[Resource]:
        """Full-text / ILIKE search over skill body + resource title/description."""
        needle = f"%{query.strip()}%"
        stmt = (
            self._base_resource_query()
            .where(Resource.is_skill.is_(True))
            .join(Resource.skill_row)
            .where(
                or_(
                    Resource.title.ilike(needle),
                    Resource.description.ilike(needle),
                    Skill.body.ilike(needle),
                )
            )
            .distinct()
        )
        if tag:
            stmt = stmt.join(Resource.tag_links).join(ResourceTag.tag).where(Tag.title.ilike(tag))
        if source:
            stmt = stmt.join(Resource.source).where(Source.title.ilike(source))
        result = await self.session.execute(stmt.limit(limit))
        return list(result.scalars().unique().all())
