import logging
import sys

from src.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.app_log_level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)

    # FastMCP installs a RichHandler at import time which wraps long messages across
    # multiple lines — unreadable in log aggregators like Fly.io. Clear all existing
    # handlers and replace with a single plain StreamHandler.
    for h in root.handlers[:]:
        root.removeHandler(h)
    root.addHandler(handler)
