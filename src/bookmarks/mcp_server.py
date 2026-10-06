"""MCP server over stdio: a thin adapter over the core.

Each tool call opens its own service (one connection per call); tools raise
`ValueError` on bad input and the SDK turns that into a tool error. The
docstrings are the contract the calling agent reads.
"""

from collections.abc import Callable
from contextlib import AbstractContextManager

from mcp.server.fastmcp import FastMCP

from bookmarks.search import Filters, Hit
from bookmarks.service import Bookmarks

OpenService = Callable[[], AbstractContextManager[Bookmarks]]


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

    return mcp
