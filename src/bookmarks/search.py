"""Hybrid search: filters narrow the candidates, then a keyword (FTS5) leg and
a vector leg rank them, fused by reciprocal rank.

`rrf` is copied from adventure-library `src/adventure_library/search.py`
(`_rrf_scored`) at commit b264b17; the executor's shape follows its
`_hybrid_rows`, minus the facet-preference leg.
"""

import re
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field

from bookmarks import store
from bookmarks.embed import Embedder, EmbedError, serialize
from bookmarks.store import Item

DEFAULT_LIMIT = 10
MAX_LIMIT = 50
# How deep each leg ranks before fusion.
_LEG_DEPTH = 100
_TOKEN = re.compile(r"\w+", re.UNICODE)
# bm25 column weights for the keyword leg.
_BM25_ENTITIES = 3.0
_BM25_TITLE = 2.0
_BM25_NOTE = 2.0
_BM25_SUMMARY = 1.0


@dataclass(frozen=True)
class Filters:
    types: Sequence[str] = ()
    domain: str | None = None
    saved_after: str | None = None  # inclusive, ISO date or timestamp
    saved_before: str | None = None  # exclusive, ISO date or timestamp
    # (model, prompt hash) now in use: admits items written by any other pair.
    stale_for: tuple[str, str] | None = None


@dataclass(frozen=True)
class Hit:
    item: Item
    score: float
    ranks: dict[str, int]


@dataclass(frozen=True)
class SearchResult:
    legs: list[str]
    hits: list[Hit]
    notes: list[str] = field(default_factory=list)


def rrf(
    rankings: Sequence[tuple[str, Sequence[int]]],
) -> tuple[list[int], dict[int, float], dict[int, dict[str, int]]]:
    """Fuse named ordered id lists and return scores plus per-leg ranks."""
    scores: dict[int, float] = {}
    leg_ranks: dict[int, dict[str, int]] = {}
    for leg_name, ranking in rankings:
        for rank, target_id in enumerate(ranking, start=1):
            scores[target_id] = scores.get(target_id, 0.0) + 1 / (60 + rank)
            leg_ranks.setdefault(target_id, {})[leg_name] = rank
    # Ties keep first-seen order: dicts keep insertion order and sorted is stable.
    ordered = sorted(scores, key=lambda target_id: -scores[target_id])
    return ordered, scores, leg_ranks


def _candidates_sql(filters: Filters) -> tuple[str, list]:
    """SELECT id FROM item narrowed by the filters."""
    clauses: list[str] = []
    params: list = []
    if filters.types:
        clauses.append(f"type IN ({','.join('?' * len(filters.types))})")
        params += [t.lower() for t in filters.types]
    if filters.domain:
        clauses.append("(domain = ? OR domain LIKE ?)")
        domain = filters.domain.lower().removeprefix("www.")
        params += [domain, f"%.{domain}"]
    if filters.saved_after:
        clauses.append("saved_at >= ?")
        params.append(filters.saved_after)
    if filters.saved_before:
        clauses.append("saved_at < ?")
        params.append(filters.saved_before)
    if filters.stale_for:
        clauses.append("(prov_model != ? OR prov_prompt_hash != ?)")
        params += filters.stale_for
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return "SELECT id FROM item" + where, params


def fts_query(query: str) -> str | None:
    """Every word as a quoted term, OR-ed: bm25 rewards items matching more."""
    tokens = _TOKEN.findall(query)
    if not tokens:
        return None
    return " OR ".join(f'"{token}"' for token in tokens)


def _fts_leg(
    conn: sqlite3.Connection, query: str, candidates: tuple[str, list]
) -> list[int]:
    match = fts_query(query)
    if match is None:
        return []
    sql, params = candidates
    rows = conn.execute(
        "SELECT rowid FROM item_fts WHERE item_fts MATCH ? "
        f"AND rowid IN ({sql}) "
        "ORDER BY bm25(item_fts, ?, ?, ?, ?) LIMIT ?",
        (
            match,
            *params,
            _BM25_TITLE,
            _BM25_SUMMARY,
            _BM25_NOTE,
            _BM25_ENTITIES,
            _LEG_DEPTH,
        ),
    ).fetchall()
    return [row[0] for row in rows]


def _vector_leg(
    conn: sqlite3.Connection,
    query_vector: list[float],
    model: str,
    candidates: tuple[str, list],
) -> list[int]:
    sql, params = candidates
    rows = conn.execute(
        "SELECT item_id FROM embedding "
        f"WHERE model = ? AND dims = ? AND item_id IN ({sql}) "
        "ORDER BY vec_distance_cosine(vector, ?) LIMIT ?",
        (model, len(query_vector), *params, serialize(query_vector), _LEG_DEPTH),
    ).fetchall()
    return [row[0] for row in rows]


def clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    if limit < 1:
        raise ValueError("limit must be at least 1")
    return min(limit, MAX_LIMIT)


def newest_items(
    conn: sqlite3.Connection, filters: Filters | None = None, limit: int | None = None
) -> list[Item]:
    """Items the filters admit, newest saved first; no query, so no ranking."""
    sql, params = _candidates_sql(filters or Filters())
    rows = conn.execute(
        f"{sql} ORDER BY saved_at DESC, id DESC LIMIT ?",
        (*params, clamp_limit(limit)),
    ).fetchall()
    return [store.get_by_id(conn, row[0]) for row in rows]


def stalest_items(
    conn: sqlite3.Connection, filters: Filters, limit: int | None = None
) -> list[Item]:
    """Items the filters admit, oldest summary first; all of them without a
    limit, because the operator, not a reader, is asking."""
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1")  # SQLite reads -1 as no limit
    sql, params = _candidates_sql(filters)
    sql += " ORDER BY prov_at, id"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    return [store.get_by_id(conn, row[0]) for row in conn.execute(sql, params)]


def hybrid_search(
    conn: sqlite3.Connection,
    embedder: Embedder,
    query: str,
    filters: Filters | None = None,
    limit: int | None = None,
) -> SearchResult:
    filters = filters or Filters()
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")
    limit = clamp_limit(limit)
    candidates = _candidates_sql(filters)
    rankings: list[tuple[str, list[int]]] = [("fts", _fts_leg(conn, query, candidates))]
    notes: list[str] = []
    try:
        query_vector = embedder.embed_query(query)
    except EmbedError as exc:
        # Degrade to keyword-only; the caller sees which legs ran.
        notes.append(f"vector leg skipped: {exc}")
    else:
        rankings.append(
            ("vector", _vector_leg(conn, query_vector, embedder.model, candidates))
        )
    ordered, scores, ranks = rrf(rankings)
    hits = []
    for item_id in ordered[:limit]:
        item = store.get_by_id(conn, item_id)
        if item is not None:
            hits.append(Hit(item=item, score=scores[item_id], ranks=ranks[item_id]))
    return SearchResult(legs=[name for name, _ in rankings], hits=hits, notes=notes)
