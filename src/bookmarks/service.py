"""The application core.

`Bookmarks` is constructed with every collaborator it uses; composition roots
(`bookmarks.cli`, the web app, the MCP server) build the production adapters
and hand them in, tests hand in fakes.
"""

import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Literal

from bookmarks import store
from bookmarks.db import now_iso, transaction
from bookmarks.embed import Embedder, EmbedReport, run_embed
from bookmarks.ingest import drain as draining
from bookmarks.ingest import lifecycle
from bookmarks.ingest.extract import clean
from bookmarks.ingest.fetch import Fetcher
from bookmarks.ingest.llm.provider import LLMProvider
from bookmarks.ingest.summarise import Prompt, load_prompt
from bookmarks.search import Filters, SearchResult, hybrid_search
from bookmarks.settings import Settings
from bookmarks.store import Item

SaveOutcome = Literal["saved", "already_saved", "requeued"]
Status = Literal["pending", "failed", "summarised"]


@dataclass(frozen=True)
class SaveResult:
    outcome: SaveOutcome
    url: str
    status: Status
    saved_at: str
    note_added: bool
    message: str


class Bookmarks:
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        settings: Settings,
        fetcher: Fetcher,
        summariser: LLMProvider,
        embedder: Embedder,
        prompt: Prompt | None = None,
    ) -> None:
        self.conn = conn
        self.settings = settings
        self.fetcher = fetcher
        self.summariser = summariser
        self.embedder = embedder
        self.prompt = prompt or load_prompt()

    def save(
        self,
        url: str,
        *,
        html: str | None = None,
        title: str | None = None,
        note: str | None = None,
        saved_at: str | None = None,
    ) -> SaveResult:
        """Keep a URL, saved now unless `saved_at` says otherwise.

        Raises `InvalidUrl` for anything but http(s)."""
        url = store.identity(url)
        note = clean(note)
        # One write lock across the lookups and the write, so a drain cannot
        # turn the URL into an item in between.
        with transaction(self.conn):
            item = store.get_by_url(self.conn, url)
            if item is not None:
                return self._already_saved(url, "summarised", item.saved_at, note)
            submission = lifecycle.get_submission(self.conn, url)
            if submission is not None and submission.status == "failed":
                return self._requeue(submission, html=html, title=title, note=note)
            if submission is not None:
                return self._already_saved(url, "pending", submission.saved_at, note)
            now = saved_at or now_iso()
            lifecycle.submit(
                self.conn,
                url,
                note=note,
                saved_at=now,
                html=html or None,
                title=clean(title),
            )
        return SaveResult(
            "saved", url, "pending", now, note_added=note is not None, message="Saved"
        )

    def _requeue(
        self,
        submission: lifecycle.Submission,
        *,
        html: str | None,
        title: str | None,
        note: str | None,
    ) -> SaveResult:
        lifecycle.requeue(
            self.conn, submission.url, html=html or None, title=clean(title)
        )
        message = "Re-queued" + ("; note not added" if note is not None else "")
        return SaveResult(
            "requeued",
            submission.url,
            "pending",
            submission.saved_at,
            note_added=False,
            message=message,
        )

    def _already_saved(
        self, url: str, status: Status, saved_at: str, note: str | None
    ) -> SaveResult:
        message = f"Already saved on {saved_at[:10]}"
        if note is not None:
            message += "; note not added"
        return SaveResult(
            "already_saved", url, status, saved_at, note_added=False, message=message
        )

    def get_item(self, item_id: int) -> Item | None:
        return store.get_by_id(self.conn, item_id)

    def list_types(self) -> list[str]:
        return store.types_in_use(self.conn)

    def drain(self, *, limit: int | None = None) -> draining.DrainReport:
        """Summarise pending submissions, oldest first, one at a time."""
        return draining.run_drain(self, limit=limit)

    def embed(self) -> EmbedReport:
        """Embed items lacking a vector for the current model."""
        return run_embed(self.conn, self.embedder)

    def search(
        self, query: str, filters: Filters | None = None, limit: int | None = None
    ) -> SearchResult:
        """Hybrid keyword + semantic search over items."""
        return hybrid_search(self.conn, self.embedder, query, filters, limit)


OpenService = Callable[[], AbstractContextManager[Bookmarks]]
