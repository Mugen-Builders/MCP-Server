from __future__ import annotations

import logging
from uuid import UUID

from src.server.server import mcp, resource_service
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# -----------------
# MCP resources
# -----------------


@mcp.resource("cartesi://health")
async def health_resource() -> dict:
    """Provides basic health and configuration metadata for this Cartesi MCP server."""
    return {
        "server": settings.app_name,
        "environment": settings.app_env,
        "mcp_base_url": settings.mcp_base_url,
        "read_only": True,
        "capabilities": {
            "resources": True,
            "tools": True,
            "prompts": True,
        },
        "content_policy": {
            "full_page_bodies_included": False,
            "resource_payloads": "metadata plus external links",
            "agent_instruction": "Fetch canonical_url or route url separately when you need page contents.",
        },
    }


@mcp.resource("cartesi://resources/{resource_id}")
async def resource_by_id(resource_id: str) -> dict:
    """Returns normalized resource metadata by database resource ID, including external links but not fetched page body text."""
    async with resource_service() as svc:
        detail = await svc.get_resource_details(UUID(resource_id), include_routes=True)
        return detail.model_dump(mode="json")


@mcp.resource("cartesi://docs/{resource_id}")
async def docs_resource(resource_id: str) -> dict:
    """Returns a documentation-focused view of a resource and its indexed routes, with route links but not fetched route body text."""
    async with resource_service() as svc:
        detail = await svc.get_resource_details(UUID(resource_id), include_routes=True)
        if detail.kind != "documentation":
            raise ValueError(f"Resource {resource_id} is not a documentation resource")
        return detail.model_dump(mode="json")


@mcp.resource("cartesi://docs/routes/{route_id}")
async def doc_route_resource(route_id: str) -> dict:
    """Returns a single documentation route and its parent resource context; fetch the returned route URL separately for full contents."""
    async with resource_service() as svc:
        return await svc.get_doc_route_detail(UUID(route_id))


@mcp.resource("cartesi://repositories/{resource_id}")
async def repository_resource(resource_id: str) -> dict:
    """Returns repository status and freshness metadata for a tracked repository resource."""
    async with resource_service() as svc:
        status = await svc.get_repository_status(UUID(resource_id))
        return status.model_dump(mode="json")


@mcp.resource("cartesi://collections/tag/{tag}")
async def collection_by_tag(tag: str) -> dict:
    """Returns a lightweight collection of resources belonging to a given tag."""
    async with resource_service() as svc:
        result = await svc.list_resources_by_tag(tag_title=tag, limit=settings.max_page_size)
        return {
            "tag": tag,
            "count": len(result.cards),
            "items": [card.model_dump(mode="json") for card in result.cards],
        }


@mcp.resource("cartesi://collections/source/{source}")
async def collection_by_source(source: str) -> dict:
    """Returns a lightweight collection of resources belonging to a given source."""
    async with resource_service() as svc:
        result = await svc.list_resources_by_source(source_title=source, limit=settings.max_page_size)
        return {
            "source": source,
            "count": len(result.cards),
            "items": [card.model_dump(mode="json") for card in result.cards],
        }

