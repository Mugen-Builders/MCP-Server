# Cartesi Knowledge MCP Server

Production-minded MCP server for exposing curated Cartesi resources from PostgreSQL to AI agents.

## What it includes

- Streamable HTTP MCP server using the official MCP Python SDK's FastMCP server
- Async SQLAlchemy database access
- Professional service-layer architecture
- MCP resources, tools, and prompts
- Search and retrieval over:
  - resources
  - repositories
  - documentation routes
  - tags
  - sources
- Health and configuration resource
- Ready for deployment behind an ASGI server or directly with `python -m src.main`

## Environment variables

Copy `.env.example` to `.env` and adjust values.

## Install

Using uv:

```bash
uv sync
```

Using pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python -m src.main
```

```bash
uv run python -m src.main
```

```bash
uv run uvicorn src.main:create_app --factory --host 0.0.0.0 --port 8000
```


This starts the MCP server on streamable HTTP at:

- `http://0.0.0.0:8000/mcp`

## Suggested client test

Use MCP Inspector or any MCP-compatible client and connect to:

```txt
http://localhost:8000/mcp
```

## Core MCP resources

- `cartesi://health`
- `cartesi://resources/{resource_id}`
- `cartesi://docs/{resource_id}`
- `cartesi://docs/routes/{route_id}`
- `cartesi://repositories/{resource_id}`
- `cartesi://collections/tag/{tag}`
- `cartesi://collections/source/{source}`

## Core tools

- `search_resources`
- `get_resource_details`
- `search_doc_routes`
- `list_doc_routes`
- `list_resources_by_tag`
- `list_resources_by_source`
- `get_repository_status`
- `get_debugging_context`
- `get_knowledge_base_summary`

## Notes

- This server is intentionally read-only.
- It reads directly from the database via a shared service layer.
- It does not depend on your admin API.
- If you already have ORM models in another package, you can replace `src/db/models.py` with imports from your shared package.
