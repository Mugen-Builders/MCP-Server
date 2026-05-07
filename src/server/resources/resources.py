from __future__ import annotations

import logging
from uuid import UUID

from src.server.server import mcp, resource_service
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _parse_uuid(value: str, field_name: str = "resource_id") -> UUID:
    """Validate and parse a UUID string, returning a helpful error message on failure."""
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        raise ValueError(
            f"Invalid {field_name}: {value!r}. Must be a UUID in the format "
            "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx. Use search_knowledge_resources "
            "or summarize_knowledge_base to discover valid resource IDs."
        )

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
                "use_for": "Discover available resources and tool usage guidance (this document).",
            },
            {
                "method": "skills_catalog",
                "uri": "cartesi://skills",
                "use_for": "List all skills for discovery — body inline at cartesi://skills/{id}.",
            },
            {
                "method": "skill_by_id",
                "uri_template": "cartesi://skills/{resource_id}",
                "use_for": "Read full skill body inline — no external URL fetch required.",
            },
            {
                "method": "article_by_id",
                "uri_template": "cartesi://articles/{resource_id}",
                "use_for": "Read full article body inline — no external URL fetch required.",
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
            # --- Orientation ---
            {
                "method": "summarize_knowledge_base",
                "use_for": "CALL FIRST — coverage counts (includes skills/articles), skills-first orientation guide.",
            },
            {
                "method": "get_knowledge_taxonomy",
                "use_for": "Get canonical tags and sources for keyword/category-driven filtering.",
            },
            # --- Skills (inline body — check before knowledge search) ---
            {
                "method": "list_skills",
                "use_for": "List all available skills with metadata. Check FIRST for task-specific content.",
            },
            {
                "method": "get_skill",
                "use_for": "Get full skill body inline — no external URL fetch needed.",
            },
            # --- Articles (inline body) ---
            {
                "method": "list_articles",
                "use_for": "List articles with optional tag/source filter.",
            },
            {
                "method": "get_article_content",
                "use_for": "Get full article body inline — no external URL fetch needed.",
            },
            # --- Search ---
            {
                "method": "search_knowledge_resources",
                "use_for": "Find relevant resources by query, kind ('repository','documentation','article','skill'), source, or tag.",
            },
            {
                "method": "search_documentation_routes",
                "use_for": "Find documentation routes across resources by query and filters.",
            },
            {
                "method": "build_debugging_context",
                "use_for": "Generate issue-focused context combining resources and routes.",
            },
            # --- Detail fetch ---
            {
                "method": "get_resource_detail",
                "use_for": "Fetch one resource by ID with normalized structure and optional routes.",
            },
            {
                "method": "list_resource_doc_routes",
                "use_for": "List route entries for one documentation resource.",
            },
            {
                "method": "list_doc_route_sections",
                "use_for": "List distinct section names for a documentation resource before using section filters.",
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
            # --- Content proxy ---
            {
                "method": "fetch_resource_content",
                "use_for": "Fetch full HTML/Markdown body for a documentation or repository URL.",
            },
            # --- Cartesi app lifecycle & version detection ---
            {
                "method": "identify_cartesi_project_version",
                "use_for": "Identify whether a project targets CLI v1.5 or v2.0-alpha from Dockerfile signals. CRITICAL: also confirms that `cartesi deploy` does NOT exist in v2.0-alpha.",
            },
            {
                "method": "get_cartesi_jsonrpc_api_reference",
                "use_for": "Get full JSON-RPC 2.0 API reference for v2.0-alpha nodes (port 10011) — all cartesi_ methods, pagination, TypeScript patterns.",
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
                "method": "get_cartesi_app_logic_guidance",
                "use_for": "Get implementation guidance for deposits, vouchers, notices, reports, portal payload decode, and msg_sender detection.",
            },
            # --- Interaction & deposits ---
            {
                "method": "send_input_to_application",
                "use_for": "Interact with a running Cartesi application by preparing InputBox/cast calls.",
            },
            {
                "method": "prepare_erc20_deposit_instructions",
                "use_for": "Prepare cast-based ERC20 deposit workflow (balance check, transfer, approve, ERC20Portal deposit).",
            },
            {
                "method": "prepare_erc721_deposit_instructions",
                "use_for": "Prepare cast/curl-based ERC721 deposit workflow (ownerOf/balanceOf, safeMint, setApprovalForAll, ERC721Portal deposit).",
            },
            {
                "method": "prepare_erc1155_deposit_instructions",
                "use_for": "Prepare cast/curl-based ERC1155 single deposit (balanceOf, mint, safeTransferFrom, ERC1155SinglePortal).",
            },
            {
                "method": "prepare_eth_deposit_instructions",
                "use_for": "Prepare cast-based ETH deposit via EtherPortal (no token approval needed).",
            },
            {
                "method": "prepare_erc1155_batch_deposit_instructions",
                "use_for": "Prepare ERC1155 batch deposit of multiple token IDs via ERC1155BatchPortal.",
            },
            {
                "method": "prepare_voucher_execution_instructions",
                "use_for": "Prepare voucher execution instructions with GraphQL proof query guidance.",
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
        "tool_groups": {
            "orientation": ["summarize_knowledge_base", "get_knowledge_taxonomy"],
            "skills": ["list_skills", "get_skill"],
            "articles": ["list_articles", "get_article_content"],
            "search": ["search_knowledge_resources", "search_documentation_routes", "build_debugging_context"],
            "detail": ["get_resource_detail", "list_resource_doc_routes", "list_doc_route_sections", "list_resources_for_tag", "list_resources_for_source", "get_repository_sync_status"],
            "content": ["fetch_resource_content"],
            "cartesi_app_lifecycle": ["identify_cartesi_project_version", "get_cartesi_jsonrpc_api_reference", "get_cartesi_app_logic_guidance", "prepare_cartesi_create_command", "prepare_cartesi_build_command", "prepare_cartesi_run_command"],
            "interaction": ["send_input_to_application"],
            "deposits": ["prepare_erc20_deposit_instructions", "prepare_erc721_deposit_instructions", "prepare_erc1155_deposit_instructions", "prepare_eth_deposit_instructions", "prepare_erc1155_batch_deposit_instructions"],
            "vouchers": ["prepare_voucher_execution_instructions"],
        },
        "recommended_flow": [
            "1. summarize_knowledge_base — orientation: counts include skills and articles",
            "2. list_skills — if skills_count > 0, check for a matching skill FIRST (body is inline)",
            "   get_skill(resource_id) — read body directly; stop here if sufficient",
            "3. [No skill] get_knowledge_taxonomy — discover valid tag and source filter values",
            "4. search_knowledge_resources or search_documentation_routes — find relevant docs/repos",
            "5. get_article_content(resource_id) — article body is inline, no URL fetch needed",
            "6. fetch_resource_content(url) — only for documentation/repository pages needing full body",
        ],
        "content_delivery_note": {
            "skills": "Body inline — get_skill returns full content directly, zero URL fetches.",
            "articles": "Body inline — get_article_content returns full content directly, zero URL fetches.",
            "documentation": "Metadata + external links — use fetch_resource_content or your web-fetch for body.",
            "repositories": "Metadata + external links — use fetch_resource_content or your web-fetch for body.",
        },
        "next_steps": [
            "Start with summarize_knowledge_base to understand counts (especially skills and articles).",
            "Call list_skills next if skills_count > 0 — skills are purpose-built for agents and have inline bodies.",
            "Use search_knowledge_resources (kind='repository'/'documentation'/'article'/'skill') for broader search.",
            "For Cartesi CLI operations: prepare_cartesi_create_command, prepare_cartesi_build_command, prepare_cartesi_run_command, send_input_to_application, and deposit tools.",
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
        detail = await svc.get_resource_details(_parse_uuid(resource_id), include_routes=True)
        return detail.model_dump(mode="json")


@mcp.resource(
    "cartesi://docs/{resource_id}",
    name="documentation_resource",
    description="Read a documentation-focused view of one resource, including indexed routes.",
)
async def docs_resource(resource_id: str) -> dict:
    """Returns a documentation-focused view of a resource and its indexed routes, with route links but not fetched route body text."""
    async with resource_service() as svc:
        detail = await svc.get_resource_details(_parse_uuid(resource_id), include_routes=True)
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
        return await svc.get_doc_route_detail(_parse_uuid(route_id, "route_id"))


@mcp.resource(
    "cartesi://repositories/{resource_id}",
    name="repository_status_resource",
    description="Read repository freshness and synchronization metadata for one repository-backed resource.",
)
async def repository_resource(resource_id: str) -> dict:
    """Returns repository status and freshness metadata for a tracked repository resource."""
    async with resource_service() as svc:
        status = await svc.get_repository_status(_parse_uuid(resource_id))
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


@mcp.resource(
    "cartesi://skills",
    name="skills_catalog",
    description="Read a catalog of all available skills. Skill bodies are inline — no external URL fetch required. Use cartesi://skills/{resource_id} for the full body.",
)
async def skills_catalog() -> dict:
    """Returns a list of all skill titles and IDs for discovery. Fetch body via cartesi://skills/{resource_id}."""
    async with resource_service() as svc:
        skills = await svc.list_skills(limit=settings.max_page_size)
        return {
            "count": len(skills),
            "note": "Skill bodies are stored inline in the database. Read cartesi://skills/{resource_id} for the full body — no external URL fetch needed.",
            "skills": skills,
        }


@mcp.resource(
    "cartesi://skills/{resource_id}",
    name="skill_by_id",
    description="Read the full inline body of a skill resource. Body is stored in the database — no external URL fetch required.",
)
async def skill_by_id(resource_id: str) -> dict:
    """Returns the full skill body inline. No external URL fetch needed."""
    async with resource_service() as svc:
        try:
            return await svc.get_skill(_parse_uuid(resource_id))
        except Exception as exc:
            raise ValueError(str(exc)) from exc


@mcp.resource(
    "cartesi://articles/{resource_id}",
    name="article_by_id",
    description="Read the full inline body of an article resource. Body is stored in the database — no external URL fetch required.",
)
async def article_by_id(resource_id: str) -> dict:
    """Returns the full article body inline. No external URL fetch needed."""
    async with resource_service() as svc:
        try:
            return await svc.get_article(_parse_uuid(resource_id))
        except Exception as exc:
            raise ValueError(str(exc)) from exc

