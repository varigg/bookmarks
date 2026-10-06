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
from bookmarks.search import Filters, SearchResult, clamp_limit, hybrid_search
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

    def find_item(
        self, *, item_id: int | None = None, url: str | None = None
    ) -> Item | None:
        """By id or by URL (normalised), exactly one of them.

        Raises `ValueError` otherwise, `InvalidUrl` for a non-http(s) URL."""
        if (item_id is None) == (url is None):
            raise ValueError("give exactly one of id or url")
        if item_id is not None:
            return store.get_by_id(self.conn, item_id)
        return store.get_by_url(self.conn, url)

    def delete_item(
        self, *, item_id: int | None = None, url: str | None = None
    ) -> Item | None:
        """Delete the item found as `find_item` finds it; None if there is none."""
        with transaction(self.conn):
            item = self.find_item(item_id=item_id, url=url)
            if item is not None:
                store.delete_item(self.conn, item.id)
        return item

    def list_items(self, limit: int | None = None) -> list[Item]:
        """Items, newest saved first."""
        return store.newest_items(self.conn, clamp_limit(limit))

    def list_submissions(
        self,
        status: Literal["pending", "failed"] | None = None,
        limit: int | None = None,
    ) -> list[lifecycle.Submission]:
        """Submissions not yet items, newest saved first."""
        return lifecycle.newest_submissions(self.conn, status, clamp_limit(limit))

    def merge_types(self, source: str, into: str) -> int:
        """Merge (or rename) a type; see `store.merge_types`."""
        with transaction(self.conn):
            return store.merge_types(self.conn, source, into)

    def list_types(self) -> dict[str, int]:
        """Every type with its item count."""
        return store.type_counts(self.conn)

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
