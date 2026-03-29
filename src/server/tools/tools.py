from __future__ import annotations

import logging
from uuid import UUID

from src.server.server import mcp, resource_service
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# -----------------
# MCP tools
# -----------------


@mcp.tool()
async def search_resources(
    query: str | None = None,
    tag: str | None = None,
    source: str | None = None,
    kind: str | None = None,
    limit: int = 10,
) -> dict:
    """Searches curated Cartesi resources and returns lightweight result cards with MCP URIs and external links, but not full page body text."""
    limit = min(max(limit, 1), settings.max_page_size)
    async with resource_service() as svc:
        result = await svc.search_resources(query=query, tag=tag, source=source, kind=kind, limit=limit)
        return {
            "status": "success",
            "summary": f"Found {len(result.cards)} matching resources.",
            "data": result.model_dump(mode="json"),
            "warnings": [
                "This server currently returns metadata and links only, not fetched page contents.",
            ],
            "next_steps": [
                "Use the returned resource URI to fetch a full resource document.",
                "Use search_doc_routes for route-level documentation lookup.",
                "If you need the source page contents, fetch the returned canonical_url separately.",
            ],
        }


@mcp.tool()
async def get_resource_details(resource_id: str, include_routes: bool = True) -> dict:
    """Fetches a fully normalized resource document by resource ID, including external links and related routes but not fetched page body text."""
    async with resource_service() as svc:
        detail = await svc.get_resource_details(UUID(resource_id), include_routes=include_routes)
        return {
            "status": "success",
            "summary": f"Loaded resource '{detail.title}'.",
            "data": detail.model_dump(mode="json"),
            "warnings": [
                "This payload does not include the full contents of the external page.",
            ],
            "next_steps": [
                "Use linked URIs to fetch related repository or documentation views.",
                "Fetch data.canonical_url separately when you need the actual page contents.",
            ],
        }


@mcp.tool()
async def list_doc_routes(resource_id: str, section: str | None = None, limit: int = 25) -> dict:
    """Lists documentation routes for a documentation resource, optionally filtered by section; results include route links but not fetched route body text."""
    limit = min(max(limit, 1), settings.max_page_size)
    async with resource_service() as svc:
        payload = await svc.list_doc_routes(UUID(resource_id), section=section, limit=limit)
        return {
            "status": "success",
            "summary": f"Found {len(payload.routes)} documentation routes for '{payload.resource_title}'.",
            "data": payload.model_dump(mode="json"),
            "warnings": [
                "Route entries expose metadata and URLs, not the fetched contents of those URLs.",
            ],
            "next_steps": [
                "Use the route URI to load one route with its parent resource context.",
                "Fetch the selected route URL separately when you need the actual doc page contents.",
            ],
        }


@mcp.tool()
async def search_doc_routes(
    query: str,
    section: str | None = None,
    source: str | None = None,
    tag: str | None = None,
    limit: int = 10,
) -> dict:
    """Searches indexed documentation routes across all tracked documentation resources and returns route metadata plus links, not fetched route body text."""
    limit = min(max(limit, 1), settings.max_page_size)
    async with resource_service() as svc:
        rows = await svc.search_doc_routes(query=query, section=section, source=source, tag=tag, limit=limit)
        return {
            "status": "success",
            "summary": f"Found {len(rows)} matching documentation routes.",
            "data": {"results": rows},
            "warnings": [
                "Search results do not include full documentation page contents.",
            ],
            "next_steps": [
                "Use the route URI to inspect a single route in more detail.",
                "Fetch the selected route URL separately when you need the actual doc page contents.",
            ],
        }


@mcp.tool()
async def list_resources_by_tag(tag_title: str, limit: int = 10) -> dict:
    """Lists resources associated with a specific tag."""
    limit = min(max(limit, 1), settings.max_page_size)
    async with resource_service() as svc:
        result = await svc.list_resources_by_tag(tag_title=tag_title, limit=limit)
        return {
            "status": "success",
            "summary": f"Found {len(result.cards)} resources tagged '{tag_title}'.",
            "data": result.model_dump(mode="json"),
            "warnings": [],
            "next_steps": [],
        }


@mcp.tool()
async def list_resources_by_source(source_title: str, limit: int = 10) -> dict:
    """Lists resources associated with a specific source, such as core contributors or community."""
    limit = min(max(limit, 1), settings.max_page_size)
    async with resource_service() as svc:
        result = await svc.list_resources_by_source(source_title=source_title, limit=limit)
        return {
            "status": "success",
            "summary": f"Found {len(result.cards)} resources for source '{source_title}'.",
            "data": result.model_dump(mode="json"),
            "warnings": [],
            "next_steps": [],
        }


@mcp.tool()
async def get_repository_status(resource_id: str) -> dict:
    """Returns sync freshness and metadata for one tracked repository resource."""
    async with resource_service() as svc:
        payload = await svc.get_repository_status(UUID(resource_id))
        return {
            "status": "success",
            "summary": f"Loaded repository status for '{payload.title}'.",
            "data": payload.model_dump(mode="json"),
            "warnings": [],
            "next_steps": [],
        }


@mcp.tool()
async def get_debugging_context(query: str, prefer_official_only: bool = False, limit: int = 8) -> dict:
    """Returns the best matching docs and resources for debugging a Cartesi issue or concept, with metadata and links for follow-up fetching."""
    limit = min(max(limit, 1), settings.max_page_size)
    async with resource_service() as svc:
        payload = await svc.get_debugging_context(query=query, prefer_official_only=prefer_official_only, limit=limit)
        return {
            "status": "success",
            "summary": "Generated debugging context from curated resources and documentation routes.",
            "data": payload,
            "warnings": [
                "The returned matches are curated pointers; fetch the linked external pages when you need full text.",
            ],
            "next_steps": [
                "Open the returned MCP URIs for full resource details.",
                "Narrow results with tags or source if you need more precision.",
                "Fetch the canonical_url or route url of the most relevant matches to inspect full contents.",
            ],
        }


@mcp.tool()
async def get_taxonomy() -> dict:
    """Returns available source names and tag names known to the knowledge base."""
    async with resource_service() as svc:
        tags = await svc.get_tag_catalog()
        sources = await svc.get_source_catalog()
        return {
            "status": "success",
            "summary": "Loaded source and tag taxonomy.",
            "data": {"tags": tags, "sources": sources},
            "warnings": [],
            "next_steps": [],
        }
    

@mcp.tool()
async def get_knowledge_base_summary() -> dict:
    """
    Returns a high-level overview of the knowledge base: counts by type,
    all tags, and all sources. Agents should call this first to orient
    themselves before searching or reading specific resources.
    """
    async with resource_service() as svc:
        summary = await svc.get_knowledge_base_summary()
        return {
            "status": "success",
            "summary": "Loaded knowledge base summary.",
            "data": {
                **summary,
                "how_to_use": {
                    "step_1": "Call get_knowledge_base_summary to understand what exists (you are here).",
                    "step_2": "Call search_resources with query/tag/source filters to find relevant items.",
                    "step_3": "Read cartesi://resources/{resource_id} for normalized metadata and related links for a specific resource.",
                    "step_4": "For documentation, use list_doc_routes or search_doc_routes to navigate sub-routes and identify the best route URL.",
                    "step_5": "Fetch canonical_url or route url separately when you need the actual page contents, since this server currently returns links rather than stored page bodies.",
                },
            },
            "warnings": [
                "This knowledge base currently provides metadata, route indexes, and external links rather than full fetched page contents.",
            ],
            "next_steps": [
                "Use search_resources to locate resources by query, tag, source, or kind.",
                "Fetch specific resource details with get_resource_details(resource_id).",
                "Fetch the returned external URLs separately when deeper content inspection is required.",
            ],
        }

