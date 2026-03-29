from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from mcp.server.fastmcp import FastMCP

from src.core.config import get_settings
from src.db.session import SessionLocal
from src.domain.resource_service import NotFoundError, ResourceService

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
        "or route url with your web-fetching capability."
    ), 
    json_response=True
    )


@asynccontextmanager
async def resource_service() -> Any:
    async with SessionLocal() as session:
        yield ResourceService(session)


# -----------------
# Error translation wrapper
# -----------------


def install_exception_logging() -> None:
    """Hook for future custom exception handling and diagnostics."""
    logger.info("MCP server initialized: %s", settings.app_name)


from src.server.resources import resources as resources_module  # noqa: F401
from src.server.tools import tools as tools_module  # noqa: F401
from src.server.prompts import prompts as prompts_module  # noqa: F401

install_exception_logging()
