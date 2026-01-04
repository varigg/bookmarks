"""Simple configuration module for the bookmarks application."""

import os
from pathlib import Path
from typing import overload

from dotenv import load_dotenv

# Find the project root
ROOT_DIR = Path(__file__).parent.parent

# Load configuration from .env files in preferred order
# 1. ~/.config/bookmarks/.env (XDG preferred location)
# 2. config/.env (project-local config)
# 3. .env (legacy root location)
load_dotenv(Path.home() / ".config" / "bookmarks" / ".env")
load_dotenv(ROOT_DIR / "config" / ".env")
load_dotenv(ROOT_DIR / ".env")


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


def resolve_path(path: str, base_dir: str) -> str:
    """Resolve a path relative to a base directory if it's not absolute.

    Args:
        path: The path to resolve
        base_dir: The base directory to resolve against

    Returns:
        The resolved absolute path or original absolute path
    """
    if not path:
        return ""
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(base_dir, path))


# Base Data Directory - defaults to current directory for local dev
DATA_DIR: str = get_config("BOOKMARKS_DATA_DIR", ".")

# Configuration with relative-to-DATA_DIR resolution
DATA_SOURCE: str = resolve_path(get_config("BOOKMARKS_DATA_SOURCE", "bookmarks.js"), DATA_DIR)
SECRET_KEY: str = get_config("BOOKMARKS_SECRET_KEY", "")
DEBUG: bool = get_config("BOOKMARKS_DEBUG", "false").lower() in ("true", "1", "yes")
PORT: int = int(get_config("BOOKMARKS_PORT", "5001"))

# Backup configuration
BACKUP_ENABLED: bool = get_config("BOOKMARKS_BACKUP_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
)
BACKUP_DIR: str = resolve_path(get_config("BOOKMARKS_BACKUP_DIR", "backup"), DATA_DIR)
BACKUP_COUNT: int = int(get_config("BOOKMARKS_BACKUP_COUNT", "5"))  # Keep last N backups

# LLM configuration
LLM_PROVIDER: str = get_config(
    "BOOKMARKS_LLM_PROVIDER", "perplexity"
)  # perplexity, perplexity-mcp, openai, anthropic
LLM_CONTENT_FORMAT: str = get_config("BOOKMARKS_LLM_CONTENT_FORMAT", "markdown")  # html, markdown
