from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.core.config import get_settings
from src.db.session import SessionLocal
from src.domain.resource_service import ResourceService

logger = logging.getLogger(__name__)
settings = get_settings()

_DEV_ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    # Browsers and clients send Host with port (e.g. localhost:8008); bare localhost does not match.
    "localhost:*",
    "127.0.0.1:*",
]

_DEV_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    # MCP Inspector and other local UIs use an explicit port (e.g. :6274).
    "http://localhost:*",
    "http://127.0.0.1:*",
]

# In production, drop localhost entries — they have no legitimate use and
# http://localhost:* in allowed_origins lets any local web page call the production server.
_is_production = settings.app_env == "production"
_BASE_ALLOWED_HOSTS = [] if _is_production else _DEV_ALLOWED_HOSTS
_BASE_ALLOWED_ORIGINS = [] if _is_production else _DEV_ALLOWED_ORIGINS

mcp = FastMCP(
    settings.app_name,
    instructions=(
        "# Cartesi Knowledge MCP Server\n\n"

        "## What This Server Does\n"
        "Provides curated Cartesi developer knowledge: repositories, documentation, articles, "
        "skills, and blog posts. Resources have sources (e.g. 'core contributors', 'community') "
        "and tags (e.g. 'docs', 'tutorial', 'sdk').\n\n"

        "IMPORTANT — content delivery model:\n"
        "- Skills and articles: body is stored inline in the DB — call get_skill or get_article_content "
        "and the full body is returned directly. No external URL fetch needed.\n"
        "- Documentation and repositories: metadata + external links only. "
        "Fetch `canonical_url` or route `url` with fetch_resource_content or your web-fetch tool "
        "when you need the actual page body.\n\n"

        "## Four Tool Groups\n"
        "1. ORIENTATION: summarize_knowledge_base, get_knowledge_taxonomy\n"
        "2. SKILLS & ARTICLES (inline body — check these first for task-specific content):\n"
        "   list_skills, get_skill, list_articles, get_article_content\n"
        "3. KNOWLEDGE RETRIEVAL (metadata + links for docs/repos):\n"
        "   search_knowledge_resources, search_documentation_routes, get_resource_detail,\n"
        "   list_resource_doc_routes, list_doc_route_sections, list_resources_for_tag,\n"
        "   list_resources_for_source, get_repository_sync_status, build_debugging_context,\n"
        "   fetch_resource_content\n"
        "4. CARTESI CLI WORKFLOW (generates instructions for the user's machine — does NOT execute):\n"
        "   identify_cartesi_project_version, get_cartesi_jsonrpc_api_reference,\n"
        "   prepare_cartesi_create_command, prepare_cartesi_build_command, prepare_cartesi_run_command,\n"
        "   send_input_to_application, prepare_erc20_deposit_instructions,\n"
        "   prepare_erc721_deposit_instructions, prepare_erc1155_deposit_instructions,\n"
        "   prepare_eth_deposit_instructions, prepare_erc1155_batch_deposit_instructions,\n"
        "   prepare_voucher_execution_instructions, get_cartesi_app_logic_guidance\n\n"

        "## CRITICAL — Cartesi CLI Version Rule\n"
        "`cartesi deploy` DOES NOT EXIST in Cartesi CLI v2.0-alpha. Never suggest it for v2.0-alpha projects. "
        "Call identify_cartesi_project_version before any deployment guidance — it returns the full "
        "Dockerfile fingerprint table, CLI capability comparison, and the correct Docker Compose deployment flow "
        "for v2.0-alpha.\n\n"

        "## Recommended Agent Flow (Skills-First)\n"
        "Step 1 → summarize_knowledge_base — orientation: counts include skills and articles.\n"
        "Step 2 → list_skills — if skills_count > 0, find a matching skill FIRST.\n"
        "         get_skill(resource_id) — body returned inline; stop here if sufficient.\n"
        "Step 3 → [No skill covers the task] get_knowledge_taxonomy — discover valid tags/sources.\n"
        "Step 4 → search_knowledge_resources or search_documentation_routes with filters.\n"
        "Step 5 → get_article_content(resource_id) — article body inline, no URL fetch.\n"
        "Step 6 → fetch_resource_content(url) — only for documentation/repository pages.\n\n"

        "## Why Skills First?\n"
        "Skills are purpose-built procedures for agent consumption, stored inline — "
        "zero external fetches, lower latency, higher reliability than interpreting raw docs.\n\n"

        "## Debugging Shortcut\n"
        "For issue debugging, call build_debugging_context — combines resources and routes "
        "in one call and is more efficient than searching manually.\n\n"

        "## MCP Resources Available\n"
        "cartesi://resources — full tool/resource/prompt catalog with tool groups and recommended flow.\n"
        "cartesi://skills — list all skill IDs and titles.\n"
        "cartesi://skills/{id} — skill body inline.\n"
        "cartesi://articles/{id} — article body inline.\n"
        "cartesi://resources/{id}, cartesi://docs/{id}, cartesi://docs/routes/{route_id} — metadata."
    ),
    json_response=True,
    host=settings.app_host,
    port=settings.app_port,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_BASE_ALLOWED_HOSTS + settings.extra_allowed_hosts,
        allowed_origins=_BASE_ALLOWED_ORIGINS + settings.extra_allowed_origins,
    ),
)

@mcp.custom_route("/health", methods=["GET"])
async def _health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})

@asynccontextmanager
async def resource_service() -> Any:
    async with SessionLocal() as session:
        yield ResourceService(session)

def install_exception_logging() -> None:
    logger.info("MCP server initialized: %s", settings.app_name)

from src.server.resources import resources as resources_module  # noqa: F401
from src.server.tools import tools as tools_module  # noqa: F401
from src.server.prompts import prompts as prompts_module  # noqa: F401

install_exception_logging()