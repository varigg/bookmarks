"""Simple configuration module for the bookmarks application."""

import os
from typing import overload


@overload
def get_config(key: str, default: str) -> str: ...


@overload
def get_config(key: str, default: None = None) -> str | None: ...


def get_config(key: str, default: str | None = None) -> str | None:
    """Get a configuration value from environment variables with a fallback default.

    Args:
        key: The configuration key (environment variable name)
        default: Default value if the environment variable is not set

    Returns:
        The configuration value
    """
    return os.environ.get(key, default)


# Configuration with sensible defaults for self-hosting
DATA_SOURCE: str = get_config("BOOKMARKS_DATA_SOURCE", "bookmarks.js")
SECRET_KEY: str = get_config("BOOKMARKS_SECRET_KEY", "")
DEBUG: bool = get_config("BOOKMARKS_DEBUG", "false").lower() in ("true", "1", "yes")
PORT: int = int(get_config("BOOKMARKS_PORT", "5001"))

# Backup configuration
BACKUP_ENABLED: bool = get_config("BOOKMARKS_BACKUP_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
)
BACKUP_DIR: str = get_config("BOOKMARKS_BACKUP_DIR", "backup")
BACKUP_COUNT: int = int(
    get_config("BOOKMARKS_BACKUP_COUNT", "5")
)  # Keep last N backups

# LLM configuration
LLM_PROVIDER: str = get_config(
    "BOOKMARKS_LLM_PROVIDER", "perplexity"
)  # perplexity, perplexity-mcp, openai, anthropic
LLM_CONTENT_FORMAT: str = get_config(
    "BOOKMARKS_LLM_CONTENT_FORMAT", "html"
)  # html, markdown
