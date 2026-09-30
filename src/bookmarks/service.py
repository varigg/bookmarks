"""The application core.

`Bookmarks` is constructed with every collaborator it uses; composition roots
(`bookmarks.cli`, the web app, the MCP server) build the production adapters
and hand them in, tests hand in fakes.
"""

import sqlite3
from dataclasses import dataclass
from typing import Literal

from bookmarks import drain as draining
from bookmarks import store
from bookmarks.clock import Clock, to_iso
from bookmarks.fetch import Fetcher
from bookmarks.llm.provider import LLMProvider
from bookmarks.settings import Settings
from bookmarks.store import Item
from bookmarks.summarise import Prompt, load_prompt
from bookmarks.urls import domain_of, normalise_url

SaveOutcome = Literal["saved", "already_saved"]


@dataclass(frozen=True)
class SaveResult:
    outcome: SaveOutcome
    item: Item
    note_added: bool
    message: str


def _clean(text: str | None) -> str | None:
    text = (text or "").strip()
    return text or None


class Bookmarks:
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        clock: Clock,
        settings: Settings,
        fetcher: Fetcher,
        summariser: LLMProvider,
        prompt: Prompt | None = None,
    ) -> None:
        self.conn = conn
        self.clock = clock
        self.settings = settings
        self.fetcher = fetcher
        self.summariser = summariser
        self.prompt = prompt or load_prompt()

    def save(
        self,
        url: str,
        *,
        html: str | None = None,
        title: str | None = None,
        note: str | None = None,
    ) -> SaveResult:
        """Keep a URL. Raises `InvalidUrl` for anything but http(s)."""
        url = normalise_url(url)
        note = _clean(note)
        existing = store.get_by_url(self.conn, url)
        if existing is not None:
            return self._already_saved(existing, note)

        now = to_iso(self.clock.now())
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            item_id = self.conn.execute(
                "INSERT INTO item (url, domain, title, note, saved_at) "
                "VALUES (?, ?, ?, ?, ?) RETURNING id",
                (url, domain_of(url), _clean(title), note, now),
            ).fetchone()[0]
            self.conn.execute(
                "INSERT INTO queue (item_id, html, capture_title, enqueued_at) "
                "VALUES (?, ?, ?, ?)",
                (item_id, html or None, _clean(title), now),
            )
            self.conn.execute("COMMIT")
        except sqlite3.IntegrityError:
            # A concurrent save of the same URL won the insert.
            self.conn.execute("ROLLBACK")
            existing = store.get_by_url(self.conn, url)
            if existing is None:
                raise
            return self._already_saved(existing, note)
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise
        item = store.get_by_id(self.conn, item_id)
        assert item is not None
        return SaveResult("saved", item, note_added=note is not None, message="Saved")

    def _already_saved(self, item: Item, note: str | None) -> SaveResult:
        message = f"Already saved on {item.saved_at[:10]}"
        if note is not None:
            message += "; note not added"
        return SaveResult("already_saved", item, note_added=False, message=message)

    def get_item(self, item_id: int) -> Item | None:
        return store.get_by_id(self.conn, item_id)

    def list_types(self) -> list[str]:
        return draining.types_in_use(self.conn)

    def drain(self, *, limit: int | None = None) -> draining.DrainReport:
        """Summarise queued items, oldest first, one at a time."""
        return draining.run_drain(self, limit=limit)
