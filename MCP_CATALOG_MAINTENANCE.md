# MCP catalog maintenance

FastMCP registers **tools**, **resources**, and **prompts** from their Python modules, but clients that rely on the **`cartesi://resources`** catalog (the `resource_catalog` resource) only see what is listed there. Keep that payload in sync whenever you extend the server surface.

## Where to update

| You add… | Also update… |
|----------|----------------|
| `@mcp.tool(...)` in `src/server/tools/tools.py` | `tools` list in `resources_catalog()` in [`src/server/resources/resources.py`](src/server/resources/resources.py) |
| `@mcp.resource(...)` in `src/server/resources/resources.py` | `resources` list in `resources_catalog()` in the same file |
| `@mcp.prompt(...)` in `src/server/prompts/prompts.py` | `prompts` list in `resources_catalog()` in [`src/server/resources/resources.py`](src/server/resources/resources.py) |

The handler is `resources_catalog()` (URI **`cartesi://resources`**, name **`resource_catalog`**). Add an entry with `method` matching the registered MCP name (tool `name=`, resource `name=`, or prompt function name) and a short `use_for` string.

## Optional follow-ups

- Adjust `next_steps` inside `resources_catalog()` when a new capability changes typical agent flows.
- Consider updating [`README.md`](README.md) if you want the human-readable tool/resource list to stay aligned (that file is not wired to the server automatically).
