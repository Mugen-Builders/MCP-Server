from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.db.models import DocRoute, Resource
from src.schemas.common import FreshnessInfo, ResourceCard, ResourceLinkSet, SourceSummary, TagSummary
from src.schemas.resources import ArticleContent, DocRouteOut, RepositoryStatus, ResourceDetail, SkillContent

STALE_AFTER_DAYS = 30


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def infer_kind(resource: Resource) -> str:
    # Explicit DB flags take priority over tag-based inference
    if resource.is_skill:
        return "skill"
    if resource.is_article:
        return "article"
    if resource.is_repository:
        return "repository"
    if resource.is_documentation:
        return "documentation"
    # Legacy fallback: articles may predate the is_article flag
    tag_titles = {link.tag.title.lower() for link in resource.tag_links}
    if {"article", "blog", "blog post", "blog-post"} & tag_titles:
        return "article"
    return "resource"


def summarize_text(resource: Resource) -> str:
    if resource.description:
        return resource.description.strip()[:240]
    # Skills and articles have inline bodies — include an excerpt in the summary
    if resource.is_skill and resource.skill_row:
        return resource.skill_row.body.strip()[:240]
    if resource.is_article and resource.article_row:
        return resource.article_row.body.strip()[:240]
    if resource.is_documentation:
        return f"Documentation resource: {resource.title}"
    if resource.is_repository:
        return f"Repository resource: {resource.title}"
    return f"Knowledge resource: {resource.title}"


def resource_links(resource: Resource) -> ResourceLinkSet:
    rid = str(resource.id)
    return ResourceLinkSet(
        self_uri=f"cartesi://resources/{rid}",
        repository_uri=f"cartesi://repositories/{rid}" if resource.is_repository else None,
        documentation_uri=f"cartesi://docs/{rid}" if resource.is_documentation else None,
        routes_uri=None,  # Use list_resource_doc_routes tool with resource_id to get routes (no resource handler registered for this URI pattern)
    )


def freshness(resource: Resource) -> FreshnessInfo:
    last_synced = resource.repository_row.last_synced_at if resource.repository_row else None
    pivot = last_synced or resource.created_at
    stale = False
    if pivot is not None:
        if pivot.tzinfo is None:
            pivot = pivot.replace(tzinfo=timezone.utc)
        stale = utcnow() - pivot > timedelta(days=STALE_AFTER_DAYS)
    return FreshnessInfo(created_at=resource.created_at, last_synced_at=last_synced, stale=stale)


def format_card(resource: Resource) -> ResourceCard:
    return ResourceCard(
        id=resource.id,
        title=resource.title,
        summary=summarize_text(resource),
        canonical_url=resource.url,
        kind=infer_kind(resource),
        source=resource.source.title,
        tags=sorted([link.tag.title for link in resource.tag_links]),
        uris=resource_links(resource),
    )


def format_doc_route(route: DocRoute) -> DocRouteOut:
    return DocRouteOut(
        id=route.id,
        name=route.name,
        section=route.section,
        url=route.url,
        description=route.description,
        created_at=route.created_at,
        uri=f"cartesi://docs/routes/{route.id}",
    )


def format_article_content(resource: Resource) -> ArticleContent | None:
    if resource.article_row is None:
        return None
    return ArticleContent(
        body=resource.article_row.body,
        year_published=resource.article_row.year_published,
        last_updated_at=resource.article_row.last_updated_at,
    )


def format_skill_content(resource: Resource) -> SkillContent | None:
    if resource.skill_row is None:
        return None
    return SkillContent(
        body=resource.skill_row.body,
        last_updated_at=resource.skill_row.last_updated_at,
    )


def format_detail(resource: Resource, include_routes: bool = True) -> ResourceDetail:
    return ResourceDetail(
        id=resource.id,
        title=resource.title,
        description=resource.description,
        canonical_url=resource.url,
        kind=infer_kind(resource),
        source=SourceSummary(id=resource.source.id, title=resource.source.title),
        tags=[TagSummary(id=link.tag.id, title=link.tag.title) for link in sorted(resource.tag_links, key=lambda x: x.tag.title.lower())],
        freshness=freshness(resource),
        uris=resource_links(resource),
        route_count=len(resource.doc_routes),
        routes=[format_doc_route(route) for route in sorted(resource.doc_routes, key=lambda r: (r.section.lower(), r.name.lower()))] if include_routes else [],
        article_content=format_article_content(resource),
        skill_content=format_skill_content(resource),
    )


def format_repository_status(resource: Resource) -> RepositoryStatus:
    if resource.repository_row is None:
        raise ValueError("Resource is not linked to a repository row")

    return RepositoryStatus(
        resource_id=resource.id,
        repository_row_id=resource.repository_row.id,
        title=resource.title,
        canonical_url=resource.url,
        source=resource.source.title,
        tags=sorted([link.tag.title for link in resource.tag_links]),
        last_synced_at=resource.repository_row.last_synced_at,
        uri=f"cartesi://repositories/{resource.id}",
    )
