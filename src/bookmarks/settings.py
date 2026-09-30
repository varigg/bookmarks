"""Settings, read once by each composition root and passed into the core."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


def _default_db_path(env: Mapping[str, str]) -> Path:
    data_home = env.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(data_home) / "bookmarks" / "bookmarks.db"


@dataclass(frozen=True)
class Settings:
    db_path: Path
    host: str = "0.0.0.0"
    port: int = 5000
    claude_executable: str = "claude"
    summariser_model: str = "claude-sonnet-5-5"
    summariser_timeout: int = 300
    # ~25K tokens at ~4 characters per token.
    source_cap_chars: int = 100_000
    fetch_timeout: float = 20.0
    # Optional; unauthenticated GitHub API calls are limited to 60 an hour.
    github_token: str | None = None
    embed_model: str = "nomic-embed-text"
    ollama_url: str = "http://127.0.0.1:11434"
    embed_timeout: float = 60.0
    # bm25 column weights for the keyword leg.
    bm25_entities: float = 3.0
    bm25_title: float = 2.0
    bm25_note: float = 2.0
    bm25_summary: float = 1.0

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        return cls(
            db_path=Path(env.get("BOOKMARKS_DB") or _default_db_path(env)),
            host=env.get("BOOKMARKS_HOST", cls.host),
            port=int(env.get("BOOKMARKS_PORT", cls.port)),
            claude_executable=env.get("BOOKMARKS_CLAUDE", cls.claude_executable),
            summariser_model=env.get(
                "BOOKMARKS_SUMMARISER_MODEL", cls.summariser_model
            ),
            summariser_timeout=int(
                env.get("BOOKMARKS_SUMMARISER_TIMEOUT", cls.summariser_timeout)
            ),
            source_cap_chars=int(
                env.get("BOOKMARKS_SOURCE_CAP_CHARS", cls.source_cap_chars)
            ),
            fetch_timeout=float(env.get("BOOKMARKS_FETCH_TIMEOUT", cls.fetch_timeout)),
            github_token=env.get("BOOKMARKS_GITHUB_TOKEN") or None,
            embed_model=env.get("BOOKMARKS_EMBED_MODEL", cls.embed_model),
            ollama_url=env.get("BOOKMARKS_OLLAMA_URL", cls.ollama_url),
            embed_timeout=float(env.get("BOOKMARKS_EMBED_TIMEOUT", cls.embed_timeout)),
            bm25_entities=float(env.get("BOOKMARKS_BM25_ENTITIES", cls.bm25_entities)),
            bm25_title=float(env.get("BOOKMARKS_BM25_TITLE", cls.bm25_title)),
            bm25_note=float(env.get("BOOKMARKS_BM25_NOTE", cls.bm25_note)),
            bm25_summary=float(env.get("BOOKMARKS_BM25_SUMMARY", cls.bm25_summary)),
        )
