# Cartesi Knowledge MCP Server

Production-minded [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes curated Cartesi developer resources — including repositories, documentation, articles, and skills — from PostgreSQL to AI agents over **streamable HTTP**.

## Current capabilities

- **FastMCP** (`mcp[cli]` 1.26.x) with `streamable_http_app()` — FastMCP's Starlette app used directly in production so session lifespan runs correctly (see `create_app()` in `src/main.py`).
- **Async SQLAlchemy** + **asyncpg** for read-only access to the knowledge database.
- **Layered layout**: config and logging (`src/core/`), DB session and models (`src/db/`), repositories, domain service (`src/domain/resource_service.py`), schemas, formatters, and server modules under `src/server/`.
- **Transport security**: DNS rebinding protection and configurable `allowed_hosts` / `allowed_origins` in `src/server/server.py`.
- **Plain HTTP health**: `GET /health` returns `{"status":"ok"}` alongside the MCP route.

### Content delivery model

| Resource type | Body delivery | Agent action needed |
|---|---|---|
| **Skills** | Inline — body stored in DB | Call `get_skill(id)` — no URL fetch |
| **Articles** | Inline — body stored in DB | Call `get_article_content(id)` — no URL fetch |
| **Documentation** | Metadata + external links | Fetch `canonical_url` / route `url` separately |
| **Repositories** | Metadata + external links | Fetch `canonical_url` separately |

**Workflow tools** (`prepare_cartesi_*`, `send_input_to_application`, `prepare_*_deposit_instructions`, `get_cartesi_app_logic_guidance`) return **instructions and command templates** for the user's machine. They do **not** run the Cartesi CLI or `cast` from this server.

## Recommended Agent Flow (Skills-First)

```
1. summarize_knowledge_base          → orientation (counts include skills + articles)
2. list_skills                       → check for a matching skill FIRST (body is inline)
   └─ get_skill(resource_id)         → read body directly — no URL fetch needed; stop here if sufficient
3. [No skill covers task] get_knowledge_taxonomy → discover valid tag/source filter values
4. search_knowledge_resources        → find repos/docs/articles by query+tag+source+kind
   └─ get_article_content(id)        → article bodies are inline (no URL fetch needed)
5. fetch_resource_content(url)       → for documentation/repository pages needing full body
```

**Why skills first?** Skills are purpose-built for agent consumption, their body is stored inline in the DB (zero external fetch latency), and they are curated validated procedures — more reliable than interpreting raw docs.

## Requirements

- Python **≥ 3.11** (see `pyproject.toml`; the included `Dockerfile` uses Python 3.12).
- PostgreSQL database with the schema managed by the `mcp-admin-server` (includes `resources`, `articles`, `skills`, `repositories`, `doc_routes`, `tags`, `sources` tables).

## Environment variables

Copy `.env.example` to `.env` and adjust. Defaults and field names are in `src/core/config.py` (notably `DATABASE_URL`, `APP_HOST`, `APP_PORT`, `MCP_BASE_URL`, pagination limits, connection pool settings). For PostgreSQL URLs, `postgres://...` is normalized to `postgresql+asyncpg://...`, and `sslmode` is translated to asyncpg-compatible `ssl`.

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

Multi-stage `Dockerfile` — installs deps with `uv`, runs `python -m src.main`. Set `DATABASE_URL` and other env vars at runtime (via `-e` or your orchestrator).

## Suggested client test

```txt
http://localhost:8000/mcp
```

---

## MCP resources

| URI | Purpose |
|-----|---------|
| `cartesi://health` | Server name, environment, `MCP_BASE_URL`, read-only flag, capabilities, content policy |
| `cartesi://resources` | **Catalog**: index of resource URIs, tool names, prompts, tool groups, and suggested agent flow |
| `cartesi://resources/{resource_id}` | Normalized resource metadata |
| `cartesi://docs/{resource_id}` | Documentation resource view |
| `cartesi://docs/routes/{route_id}` | Single doc route with parent context |
| `cartesi://repositories/{resource_id}` | Repository sync / freshness metadata |
| `cartesi://collections/tag/{tag}` | Resources grouped by tag |
| `cartesi://collections/source/{source}` | Resources grouped by source |
| `cartesi://skills` | List all available skills for discovery |
| `cartesi://skills/{resource_id}` | Skill body inline (no external fetch required) |
| `cartesi://articles/{resource_id}` | Article body inline (no external fetch required) |

---

## MCP tools

### Orientation (call first)

- `summarize_knowledge_base` — coverage counts (including skills/articles), orientation guide. **Call this first.**
- `get_knowledge_taxonomy` — canonical tag and source titles for filtering

### Skills (check before knowledge search — body is inline)

- `list_skills` — list all skills with title, description, tags
- `get_skill` — **full skill body returned inline**, no URL fetch required

### Articles (body inline)

- `list_articles` — list articles with optional tag/source filter
- `get_article_content` — **full article body returned inline**, no URL fetch required

### Search

- `search_knowledge_resources` — search by query, tag, source, kind (`repository`, `documentation`, `article`, `skill`)
- `search_documentation_routes` — search routes across resources
- `build_debugging_context` — issue-focused bundle of resources and routes

### Detail fetch

- `get_resource_detail` — one resource by ID, with optional routes
- `list_resource_doc_routes` — routes for a documentation resource
- `list_doc_route_sections` — distinct section names for a documentation resource
- `list_resources_for_tag` / `list_resources_for_source`
- `get_repository_sync_status`

### Content proxy

- `fetch_resource_content` — fetch and return external URL body (docs.cartesi.io, github.com, etc.)

### Cartesi app lifecycle (host-side instructions only)

- `prepare_cartesi_create_command` — stable v1.5.x vs alpha v2.0 create guidance
- `prepare_cartesi_build_command`
- `prepare_cartesi_run_command`
- `get_cartesi_app_logic_guidance` — address-book, portals, vouchers, notices, reports

### Interaction & deposits (host-side instructions only)

- `send_input_to_application` — InputBox + `cast` templates
- `prepare_erc20_deposit_instructions` — ERC20Portal flow
- `prepare_erc721_deposit_instructions` — ERC721Portal flow
- `prepare_erc1155_deposit_instructions` — ERC1155SinglePortal flow
- `prepare_eth_deposit_instructions` — EtherPortal flow
- `prepare_erc1155_batch_deposit_instructions` — ERC1155BatchPortal flow
- `prepare_voucher_execution_instructions` — voucher execution with GraphQL proof query

---

## MCP prompts

- `debug_cartesi_issue` — structured debugging using curated knowledge
- `find_cartesi_docs` — doc route discovery for a topic
- `explain_repository_context` — repository resource + status summary

---

## Developer notes

- Agent-facing documentation, implementation tracker, and optimization plan live in **`.agents/`** (git-ignored, local only). Start with `.agents/INDEX.md`.
- Before adding a new tool or resource, read `.agents/MCP_CATALOG_MAINTENANCE.md` — catalog entries must be kept in sync manually.
- The `kind` field on resources: `"repository"`, `"documentation"`, `"article"`, `"skill"`, `"resource"`.
