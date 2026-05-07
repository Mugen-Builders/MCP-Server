from __future__ import annotations

import logging
from uuid import UUID

from src.server.server import mcp, resource_service
from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# -----------------
# MCP prompts
# -----------------


@mcp.prompt()
def debug_cartesi_issue(issue_description: str, prefer_official_only: bool = True) -> str:
    """Creates a reusable prompt for investigating a Cartesi issue using the latest curated knowledge."""
    trust_hint = "official and core-contributor resources only" if prefer_official_only else "all available curated resources"
    return (
        "You are investigating a Cartesi issue. "
        f"Use {trust_hint}. "
        f"Start by calling build_debugging_context with this issue description: {issue_description!r}. "
        "Then inspect the top resource and route URIs that seem most relevant. "
        "This server currently returns metadata and links rather than stored page bodies, "
        "so fetch the canonical_url or route url separately when you need the actual contents. "
        "Prefer concise causal reasoning, reference the resource provenance, and distinguish official docs from community material."
    )


@mcp.prompt()
def find_cartesi_docs(topic: str, section: str | None = None) -> str:
    """Creates a prompt that guides an agent to find the best documentation for a Cartesi topic."""
    suffix = (
        f" Limit route search to the section {section!r} — but first call get_knowledge_taxonomy "
        "to verify this section name exists before filtering by it."
        if section
        else ""
    )
    return (
        f"Find the best Cartesi documentation for the topic {topic!r}. "
        "Start by calling summarize_knowledge_base to orient yourself, then call search_documentation_routes. "
        "For the most relevant route or two, fetch the route URL separately for the actual documentation contents. "
        f"Focus on official docs (source: 'core contributors') before community material.{suffix}"
    )


@mcp.prompt()
def explain_repository_context(repository_resource_id: str) -> str:
    """Creates a prompt for understanding a tracked repository and its surrounding context."""
    return (
        f"Explain the tracked repository with resource ID {repository_resource_id!r}. "
        "Call get_repository_sync_status and get_resource_detail for this resource ID. "
        "Summarize what the repository is, its source, its tags, and what documentation resources are adjacent. "
        "If freshness.stale is true, warn the user that the repository metadata may be outdated and suggest fetching the canonical_url for current information. "
        "If you need the repository page contents, fetch the returned canonical_url separately."
    )
