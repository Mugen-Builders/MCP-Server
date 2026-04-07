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


@mcp.resource(
    "cartesi://health",
    name="mcp_server_health",
    description="Read server health, capability flags, and content policy for this Cartesi MCP server.",
)
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


@mcp.resource(
    "cartesi://resources",
    name="resource_catalog",
    description="Read a concrete discoverable catalog of available knowledge resources.",
)
async def resources_catalog() -> dict:
    """Returns a discoverable index of available resources and tools with usage guidance."""
    return {
        "resources": [
            {
                "method": "mcp_server_health",
                "uri": "cartesi://health",
                "use_for": "Check server health, capabilities, and content policy.",
            },
            {
                "method": "resource_catalog",
                "uri": "cartesi://resources",
                "use_for": "Discover available resources and tool usage guidance.",
            },
            {
                "method": "resource_by_id",
                "uri_template": "cartesi://resources/{resource_id}",
                "use_for": "Read full normalized metadata for one resource.",
            },
            {
                "method": "documentation_resource",
                "uri_template": "cartesi://docs/{resource_id}",
                "use_for": "Read documentation-specific view of a resource and its routes.",
            },
            {
                "method": "documentation_route_by_id",
                "uri_template": "cartesi://docs/routes/{route_id}",
                "use_for": "Read one documentation route with parent resource context.",
            },
            {
                "method": "repository_status_resource",
                "uri_template": "cartesi://repositories/{resource_id}",
                "use_for": "Read repository sync freshness and related metadata.",
            },
            {
                "method": "tag_collection",
                "uri_template": "cartesi://collections/tag/{tag}",
                "use_for": "Read resources grouped by a specific tag.",
            },
            {
                "method": "source_collection",
                "uri_template": "cartesi://collections/source/{source}",
                "use_for": "Read resources grouped by a specific source.",
            },
        ],
        "tools": [
            {
                "method": "summarize_knowledge_base",
                "use_for": "Get high-level coverage, counts, and orientation before deep retrieval.",
            },
            {
                "method": "get_knowledge_taxonomy",
                "use_for": "Get canonical tags and sources for keyword/category-driven filtering.",
            },
            {
                "method": "search_knowledge_resources",
                "use_for": "Find relevant resources by query, kind, source, or tag.",
            },
            {
                "method": "get_resource_detail",
                "use_for": "Fetch one resource by ID with normalized structure and optional routes.",
            },
            {
                "method": "list_resource_doc_routes",
                "use_for": "List route entries for one documentation resource.",
            },
            {
                "method": "search_documentation_routes",
                "use_for": "Find documentation routes across resources by query and filters.",
            },
            {
                "method": "list_resources_for_tag",
                "use_for": "List resources for a specific tag title.",
            },
            {
                "method": "list_resources_for_source",
                "use_for": "List resources for a specific source title.",
            },
            {
                "method": "get_repository_sync_status",
                "use_for": "Inspect freshness/sync status for repository-backed resources.",
            },
            {
                "method": "build_debugging_context",
                "use_for": "Generate issue-focused context combining resources and routes.",
            },
            {
                "method": "prepare_cartesi_create_command",
                "use_for": "Bootstrap/create/initialize a Cartesi application on the user's machine.",
            },
            {
                "method": "prepare_cartesi_build_command",
                "use_for": "Build a Cartesi application on the user's machine.",
            },
            {
                "method": "prepare_cartesi_run_command",
                "use_for": "Run a Cartesi application on the user's machine.",
            },
            {
                "method": "send_input_to_application",
                "use_for": "Interact with a running Cartesi application by preparing InputBox/cast calls.",
            },
            {
                "method": "prepare_erc20_deposit_instructions",
                "use_for": "Prepare cast-based ERC20 deposit workflow (balance check, transfer, approve, ERC20Portal deposit) on the user's machine.",
            },
            {
                "method": "prepare_erc721_deposit_instructions",
                "use_for": "Prepare cast/curl-based ERC721 deposit workflow (ownerOf/balanceOf, safeMint, transferFrom, setApprovalForAll, ERC721Portal deposit) on the user's machine.",
            },
            {
                "method": "prepare_erc1155_deposit_instructions",
                "use_for": "Prepare cast/curl-based ERC1155 single deposit (balanceOf, mint, safeTransferFrom, setApprovalForAll, ERC1155SinglePortal) on the user's machine.",
            },
            {
                "method": "get_cartesi_app_logic_guidance",
                "use_for": "Get implementation guidance for deposits, vouchers, notices, reports, and portal flows.",
            },
        ],
        "prompts": [
            {
                "method": "debug_cartesi_issue",
                "use_for": "Structured starting point for debugging a Cartesi issue using curated knowledge.",
            },
            {
                "method": "find_cartesi_docs",
                "use_for": "Guide discovery of documentation routes for a Cartesi topic.",
            },
            {
                "method": "explain_repository_context",
                "use_for": "Summarize a tracked repository resource and adjacent context.",
            },
        ],
        "next_steps": [
            "Start with summarize_knowledge_base and get_knowledge_taxonomy to orient and pick filters.",
            "Use search_knowledge_resources or search_documentation_routes to find relevant items.",
            "Use get_resource_detail or cartesi://resources/{resource_id} for detailed resource payloads.",
            "If your task is Cartesi app lifecycle operations, use prepare_cartesi_create_command, prepare_cartesi_build_command, prepare_cartesi_run_command, send_input_to_application, prepare_erc20_deposit_instructions for ERC20, prepare_erc721_deposit_instructions for ERC721, and prepare_erc1155_deposit_instructions for ERC1155 single deposits.",
        ],
    }


@mcp.resource(
    "cartesi://resources/{resource_id}",
    name="resource_by_id",
    description="Read a normalized resource payload by resource ID.",
)
async def resource_by_id(resource_id: str) -> dict:
    """Returns normalized resource metadata by database resource ID, including external links but not fetched page body text."""
    async with resource_service() as svc:
        detail = await svc.get_resource_details(UUID(resource_id), include_routes=True)
        return detail.model_dump(mode="json")


@mcp.resource(
    "cartesi://docs/{resource_id}",
    name="documentation_resource",
    description="Read a documentation-focused view of one resource, including indexed routes.",
)
async def docs_resource(resource_id: str) -> dict:
    """Returns a documentation-focused view of a resource and its indexed routes, with route links but not fetched route body text."""
    async with resource_service() as svc:
        detail = await svc.get_resource_details(UUID(resource_id), include_routes=True)
        if detail.kind != "documentation":
            raise ValueError(f"Resource {resource_id} is not a documentation resource")
        return detail.model_dump(mode="json")


@mcp.resource(
    "cartesi://docs/routes/{route_id}",
    name="documentation_route_by_id",
    description="Read one documentation route with parent resource context.",
)
async def doc_route_resource(route_id: str) -> dict:
    """Returns a single documentation route and its parent resource context; fetch the returned route URL separately for full contents."""
    async with resource_service() as svc:
        return await svc.get_doc_route_detail(UUID(route_id))


@mcp.resource(
    "cartesi://repositories/{resource_id}",
    name="repository_status_resource",
    description="Read repository freshness and synchronization metadata for one repository-backed resource.",
)
async def repository_resource(resource_id: str) -> dict:
    """Returns repository status and freshness metadata for a tracked repository resource."""
    async with resource_service() as svc:
        status = await svc.get_repository_status(UUID(resource_id))
        return status.model_dump(mode="json")


@mcp.resource(
    "cartesi://collections/tag/{tag}",
    name="tag_collection",
    description="Read a lightweight collection of resources grouped by tag.",
)
async def collection_by_tag(tag: str) -> dict:
    """Returns a lightweight collection of resources belonging to a given tag."""
    async with resource_service() as svc:
        result = await svc.list_resources_by_tag(tag_title=tag, limit=settings.max_page_size)
        return {
            "tag": tag,
            "count": len(result.cards),
            "items": [card.model_dump(mode="json") for card in result.cards],
        }


@mcp.resource(
    "cartesi://collections/source/{source}",
    name="source_collection",
    description="Read a lightweight collection of resources grouped by source.",
)
async def collection_by_source(source: str) -> dict:
    """Returns a lightweight collection of resources belonging to a given source."""
    async with resource_service() as svc:
        result = await svc.list_resources_by_source(source_title=source, limit=settings.max_page_size)
        return {
            "source": source,
            "count": len(result.cards),
            "items": [card.model_dump(mode="json") for card in result.cards],
        }

