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

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        return cls(
            db_path=Path(env.get("BOOKMARKS_DB") or _default_db_path(env)),
            host=env.get("BOOKMARKS_HOST", cls.host),
            port=int(env.get("BOOKMARKS_PORT", cls.port)),
        )
