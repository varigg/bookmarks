"""MCP server over stdio: a thin adapter over the core.

Each tool call opens its own service (one connection per call); tools raise
`ValueError` on bad input and the SDK turns that into a tool error. The
docstrings are the contract the calling agent reads.
"""

from typing import Literal

from mcp.server.fastmcp import FastMCP

from bookmarks import store
from bookmarks.ingest.lifecycle import Submission
from bookmarks.search import Filters, Hit
from bookmarks.service import OpenService
from bookmarks.store import Item


def _hit(hit: Hit) -> dict:
    item = hit.item
    return {
        "id": item.id,
        "url": item.url,
        "title": item.title,
        "type": item.type,
        "domain": item.domain,
        "saved_at": item.saved_at,
        "summary": item.summary,
        "entities": item.entities,
        "note": item.note,
        "score": round(hit.score, 6),
        "ranks": hit.ranks,
    }


def _listed(item: Item) -> dict:
    return {
        "id": item.id,
        "url": item.url,
        "title": item.title,
        "type": item.type,
        "lede": store.lede(item.summary),
        "saved_at": item.saved_at,
    }


def _record(item: Item) -> dict:
    p = item.provenance
    return {
        "id": item.id,
        "url": item.url,
        "title": item.title,
        "type": item.type,
        "domain": item.domain,
        "saved_at": item.saved_at,
        "summary": item.summary,
        "entities": item.entities,
        "note": item.note,
        "provenance": {
            "cli": p.cli,
            "model": p.model,
            "prompt_hash": p.prompt_hash,
            "at": p.at,
            "truncated": p.truncated,
        },
        "archive_url": store.archive_url(item.url),
    }


def _submission(sub: Submission) -> dict:
    return {
        "url": sub.url,
        "status": sub.status,
        "saved_at": sub.saved_at,
        "note": sub.note,
        "failure_reason": sub.failure_reason,
    }


def build_server(open_service: OpenService) -> FastMCP:
    mcp = FastMCP("bookmarks")

    @mcp.tool()
    def search(
        query: str,
        types: list[str] | None = None,
        domain: str | None = None,
        saved_after: str | None = None,
        saved_before: str | None = None,
        limit: int = 10,
    ) -> dict:
        """Find saved items by describing them loosely or naming an exact term.

        Hybrid search: a keyword leg (exact names, entities, terms of art) and
        a semantic leg (meaning), fused by reciprocal rank. There is no
        relevance cutoff: judge relevance from each result's summary and
        score. Every result carries the full summary, entities, the user's own
        note, the fused `score` and `ranks` (its rank in each leg that found it).

        Filters narrow the candidates before ranking:
        - types: item types, e.g. ["article", "repo"]
        - domain: e.g. "github.com" (subdomains match too)
        - saved_after / saved_before: ISO dates, e.g. "2026-01-01";
          after is inclusive, before exclusive
        - limit: default 10, at most 50

        Returns {legs, results, notes}; `legs` names the ranking legs that ran
        and `notes` explains any that were skipped.
        """
        filters = Filters(
            types=types or (),
            domain=domain,
            saved_after=saved_after,
            saved_before=saved_before,
        )
        with open_service() as svc:
            result = svc.search(query, filters, limit)
        return {
            "legs": result.legs,
            "results": [_hit(hit) for hit in result.hits],
            "notes": result.notes,
        }

    @mcp.tool()
    def list_items(limit: int = 10) -> dict:
        """List saved items, newest first, each with its lede (the summary's
        first sentence). Only summarised items; URLs still waiting or failed
        are in `list_submissions`. limit: default 10, at most 50."""
        with open_service() as svc:
            items = svc.list_items(limit)
        return {"items": [_listed(item) for item in items]}

    @mcp.tool()
    def get_item(id: int | None = None, url: str | None = None) -> dict:
        """Get one item's full record by `id` or by `url` (give exactly one;
        the URL may carry tracking parameters or a fragment). Includes its
        provenance (which CLI, model and prompt wrote the summary) and an
        `archive_url` on the Wayback Machine. Errors if there is no item."""
        with open_service() as svc:
            item = svc.find_item(item_id=id, url=url)
        if item is None:
            raise ValueError("no item with that id or url")
        return _record(item)

    @mcp.tool()
    def save_item(url: str, note: str | None = None) -> dict:
        """Save a URL to be summarised later; it shows in `list_submissions`
        until it becomes an item.

        `note` must be the user's own words saying why they kept it, passed
        through as they said them. Never write a note yourself; omit it if
        the user gave none.

        Saving a URL that is already saved changes nothing ("Already saved"),
        and never adds the note; saving a failed URL re-queues it."""
        with open_service() as svc:
            result = svc.save(url, note=note)
        return {
            "outcome": result.outcome,
            "message": result.message,
            "note_added": result.note_added,
            "url": result.url,
            "status": result.status,
            "saved_at": result.saved_at,
        }

    @mcp.tool()
    def delete_item(id: int | None = None, url: str | None = None) -> dict:
        """Delete one item by `id` or `url` (give exactly one). It is gone from
        lists and search for good. Returns the deleted item's id, url and
        title; errors if there is no item."""
        with open_service() as svc:
            item = svc.delete_item(item_id=id, url=url)
        if item is None:
            raise ValueError("no item with that id or url")
        return {"deleted": {"id": item.id, "url": item.url, "title": item.title}}

    @mcp.tool()
    def list_types() -> dict:
        """Every item type with how many items have it, including types with
        none. Use these names for search's `types` filter."""
        with open_service() as svc:
            counts = svc.list_types()
        return {"types": [{"name": n, "count": c} for n, c in counts.items()]}

    @mcp.tool()
    def merge_types(source: str, into: str) -> dict:
        """Merge the type `source` into the type `into`: every item of `source`
        moves to `into`, and `source` is retired for good (a later summary
        naming it is stored as `into`). If `into` is not an existing type,
        this renames `source`. Names are case-insensitive.

        Errors if `source` is not a type, is the same as `into`, or `into` is
        itself a merged-away name. Returns how many items moved."""
        with open_service() as svc:
            moved = svc.merge_types(source, into)
        return {"moved": moved}

    @mcp.tool()
    def list_submissions(
        status: Literal["pending", "failed"] | None = None, limit: int = 10
    ) -> dict:
        """List saved URLs that are not items yet, newest first: pending
        (waiting to be summarised) or failed (with a `failure_reason` naming
        the stage that failed). Saving a failed URL again retries it.
        status: narrow to "pending" or "failed". limit: default 10, at most 50."""
        with open_service() as svc:
            subs = svc.list_submissions(status, limit)
        return {"submissions": [_submission(sub) for sub in subs]}

    return mcp
