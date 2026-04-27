# Cartesi Knowledge MCP Server

Production-minded [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes curated Cartesi developer resources from PostgreSQL to AI agents over **streamable HTTP**.

## Current capabilities

- **FastMCP** (`mcp[cli]` 1.26.x) with `streamable_http_app()` — use FastMCP’s Starlette app directly in production so session lifespan runs correctly (see `create_app()` in `src/main.py`).
- **Async SQLAlchemy** + **asyncpg** for read-only access to the knowledge database.
- **Layered layout**: config and logging (`src/core/`), DB session and models (`src/db/`), repositories, domain service (`src/domain/resource_service.py`), schemas, formatters, and server modules under `src/server/`.
- **Transport security**: DNS rebinding protection and configurable `allowed_hosts` / `allowed_origins` in `src/server/server.py` (extend for your deployment hostname).
- **Plain HTTP health**: `GET /healthz` returns `{"status":"ok"}` alongside the MCP route.

Knowledge responses are **metadata and links** (titles, URIs, `canonical_url`, doc routes). They do **not** include full fetched page bodies; agents should fetch external URLs when they need raw HTML or markdown.

**Workflow tools** (`prepare_cartesi_*`, `send_input_to_application`, `prepare_*_deposit_instructions`, `get_cartesi_app_logic_guidance`) only return **instructions and command templates** for the user’s machine. They do **not** run the Cartesi CLI, `cast`, or chain RPC from this server.

## Requirements

- Python **≥ 3.11** (see `pyproject.toml`; the included `Dockerfile` uses Python 3.12).
- A PostgreSQL database populated with the curated resource schema expected by `src/db/models.py` and `ResourceService`.

## Environment variables

Copy `.env.example` to `.env` and adjust. Defaults and field names are defined in `src/core/config.py` (notably `DATABASE_URL`, `APP_HOST`, `APP_PORT`, `MCP_BASE_URL`, pagination limits). For PostgreSQL URLs, `postgres://...` is normalized to `postgresql+asyncpg://...`, and `sslmode` is translated to asyncpg-compatible `ssl` (for example, `sslmode=disable` becomes `ssl=false`).

## Install

Using [uv](https://github.com/astral-sh/uv) (recommended):

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

The MCP endpoint is streamable HTTP at:

- `http://<host>:<port>/mcp` (default: `http://0.0.0.0:8000/mcp`)

## Docker

The repository includes a multi-stage `Dockerfile` that installs dependencies with `uv` and runs `python -m src.main`. Set `DATABASE_URL` and other env vars at runtime (for example via `-e` or your orchestrator).

## Suggested client test

Use MCP Inspector or any MCP-compatible client and connect to:

```txt
http://localhost:8000/mcp
```

## MCP resources

| URI                                     | Purpose                                                                                |
| --------------------------------------- | -------------------------------------------------------------------------------------- |
| `cartesi://health`                      | Server name, environment, `MCP_BASE_URL`, read-only flag, capabilities, content policy |
| `cartesi://resources`                   | **Catalog**: index of resource URIs, tool names, prompts, and suggested agent flow     |
| `cartesi://resources/{resource_id}`     | Normalized resource metadata                                                           |
| `cartesi://docs/{resource_id}`          | Documentation resource view (same shape; non-doc IDs error)                            |
| `cartesi://docs/routes/{route_id}`      | Single doc route with parent context                                                   |
| `cartesi://repositories/{resource_id}`  | Repository sync / freshness metadata                                                   |
| `cartesi://collections/tag/{tag}`       | Resources grouped by tag                                                               |
| `cartesi://collections/source/{source}` | Resources grouped by source                                                            |

## MCP tools (registered names)

These are the **`name=` values** clients see (Python handler names may differ).

**Knowledge**

- `summarize_knowledge_base` — coverage, counts, orientation
- `get_knowledge_taxonomy` — known tag and source titles
- `search_knowledge_resources` — search by query, tag, source, kind
- `get_resource_detail` — one resource by ID, optional routes
- `list_resource_doc_routes` — routes for a documentation resource
- `search_documentation_routes` — search routes across resources
- `list_resources_for_tag` / `list_resources_for_source`
- `get_repository_sync_status`
- `build_debugging_context` — issue-focused bundle of resources and routes

**Host-side Cartesi workflow (instructions only)**

- `prepare_cartesi_create_command` — stable v1.5.x vs alpha v2.0 create guidance
- `prepare_cartesi_build_command`
- `prepare_cartesi_run_command`
- `send_input_to_application` — InputBox + `cast` templates
- `prepare_erc20_deposit_instructions` — ERC20Portal flow
- `prepare_erc721_deposit_instructions` — ERC721Portal flow
- `prepare_erc1155_deposit_instructions` — ERC1155SinglePortal flow
- `get_cartesi_app_logic_guidance` — address-book, portals, vouchers, notices, reports

## MCP prompts

- `debug_cartesi_issue` — structured debugging using curated knowledge
- `find_cartesi_docs` — doc route discovery for a topic
- `explain_repository_context` — repository resource + status summary
