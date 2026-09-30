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
        )
