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

mcp = FastMCP(
    settings.app_name,
    instructions=(
        "This server exposes a structured knowledge base of developer resources: "
        "repositories, articles, documentation, and blog posts. Each resource has "
        "a source (e.g. core contributors, community) and tags (e.g. docs, tutorial). "
        "Use the search and list tools to discover resources, then read a specific "
        "resource URI to get normalized metadata and related doc routes. This server "
        "currently returns curated metadata and external links, not full page bodies. "
        "When you need the actual contents of a page, fetch the returned canonical_url "
        "or route url with your web-fetching capability. Cartesi workflow helper tools "
        "in this server only generate instructions and commands for the user's own "
        "machine; they do not execute the Cartesi CLI on this server. When implementing "
        "Cartesi application logic involving deposits, vouchers, notices, reports, or "
        "portal interactions, have the agent run `cartesi address-book` on the user's "
        "machine and consult relevant docs/tutorial resources for context."
    ),
    json_response=True,
    host=settings.app_host,
    port=settings.app_port,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            # Browsers and clients send Host with port (e.g. localhost:8008); bare localhost does not match.
            "localhost:*",
            "127.0.0.1:*",
            "cartesi-mcp.idogwuchinonso.com",
            # Accept the same host on any port (curl to :8001 sometimes includes the port in Host header).
            "cartesi-mcp.idogwuchinonso.com:*",
            "cartesi-mcp.idogwuchinonso.com:80",
            "cartesi-mcp.idogwuchinonso.com:443",
            "cartesi-mcp.idogwuchinonso.com:8001",
        ],
        allowed_origins=[
            "http://localhost",
            "http://127.0.0.1",
            # MCP Inspector and other local UIs use an explicit port (e.g. :6274).
            "http://localhost:*",
            "http://127.0.0.1:*",
            "http://cartesi-mcp.idogwuchinonso.com",
            "https://cartesi-mcp.idogwuchinonso.com",
        ],
    ),
)

@mcp.custom_route("/healthz", methods=["GET"])
async def _healthz(_request: Request) -> JSONResponse:
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