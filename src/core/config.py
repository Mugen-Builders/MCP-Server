from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url_for_async(url: str) -> str:
    u = url.strip()
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://") :]
    if u.startswith("postgresql://") and not u.startswith("postgresql+"):
        u = "postgresql+asyncpg://" + u[len("postgresql://") :]

    # SQLAlchemy's asyncpg dialect forwards URL query params as kwargs to
    # asyncpg's connect(). asyncpg.connect() accepts `ssl` but not `sslmode`,
    # so rename sslmode→ssl while keeping the value as a valid SSLMode string
    # (disable, allow, prefer, require, verify-ca, verify-full).
    if u.startswith("postgresql+asyncpg://"):
        parsed = urlsplit(u)
        query = parse_qsl(parsed.query, keep_blank_values=True)
        if any(key == "sslmode" for key, _ in query):
            query = [
                ("ssl", value) if key == "sslmode" else (key, value)
                for key, value in query
            ]
            u = urlunsplit((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                urlencode(query, doseq=True),
                parsed.fragment,
            ))
    return u


class Settings(BaseSettings):
    app_name: str = Field(default="Cartesi Knowledge MCP Server", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")
    mcp_base_url: str = Field(default="http://localhost:8000/mcp", alias="MCP_BASE_URL")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/cartesi_mcp",
        alias="DATABASE_URL",
    )
    default_page_size: int = Field(default=10, alias="DEFAULT_PAGE_SIZE")
    max_page_size: int = Field(default=50, alias="MAX_PAGE_SIZE")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, v: object) -> object:
        if not isinstance(v, str):
            return v
        return normalize_database_url_for_async(v)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
