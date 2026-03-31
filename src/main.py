import uvicorn  # pyright: ignore[reportMissingImports]

from src.core.config import get_settings
from src.core.logging import configure_logging
from src.server.server import mcp


def create_app():
    # Use FastMCP's Starlette app directly so its lifespan runs StreamableHTTPSessionManager.run().
    # Nesting this app under another Starlette app skips that lifespan and breaks MCP HTTP.
    return mcp.streamable_http_app()


def main() -> None:
    settings = get_settings()
    configure_logging()
    uvicorn.run(create_app(), host=settings.app_host, port=settings.app_port)


if __name__ == "__main__":
    main()
