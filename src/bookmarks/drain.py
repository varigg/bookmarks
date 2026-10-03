"""The drain: claim queued items one at a time and summarise them.

The claim protocol (atomic `UPDATE ... RETURNING`, stale-claim recovery at
startup, concurrency of one) is adapted from adventure-library
`src/adventure_library/jobs.py` and `worker.py` at commit b264b17.
"""

import json
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bookmarks.acquire import Acquired, acquire
from bookmarks.clock import to_iso
from bookmarks.db import transaction
from bookmarks.fetch import Unacquirable
from bookmarks.llm.provider import PAUSE_CLASSES, ProviderFailure
from bookmarks.summarise import (
    InvalidReply,
    Summary,
    Unreadable,
    build_request,
    cap_source,
    parse_reply,
)

if TYPE_CHECKING:
    from bookmarks.service import Bookmarks


@dataclass(frozen=True)
class Claim:
    item_id: int
    url: str
    html: str | None
    capture_title: str | None
    attempts: int


MAX_ATTEMPTS = 3
# Copied from adventure-library worker.py (b264b17): stop after this many
# consecutive failures, so an unrecognised outage costs a few items one
# attempt each rather than burning the whole queue's retry budget.
BREAKER_THRESHOLD = 5


@dataclass
class DrainReport:
    summarised: int = 0
    failed: int = 0
    retry: int = 0
    stopped: str | None = None


def recover_stale(conn: sqlite3.Connection) -> None:
    """Concurrency of one: any claim still held at startup is a dead run's."""
    conn.execute("UPDATE queue SET claimed_at = NULL WHERE claimed_at IS NOT NULL")


def claim_next(
    conn: sqlite3.Connection, now: str, *, exclude: set[int] = frozenset()
) -> Claim | None:
    skip = ",".join("?" * len(exclude))
    row = conn.execute(
        "UPDATE queue SET claimed_at = ? "
        "WHERE item_id = (SELECT item_id FROM queue WHERE claimed_at IS NULL "
        f"                 AND item_id NOT IN ({skip}) "
        "                 ORDER BY enqueued_at, item_id LIMIT 1) "
        "AND claimed_at IS NULL "
        "RETURNING item_id, html, capture_title, attempts",
        (now, *exclude),
    ).fetchone()
    if row is None:
        return None
    url = conn.execute(
        "SELECT url FROM item WHERE id = ?", (row["item_id"],)
    ).fetchone()["url"]
    return Claim(
        item_id=row["item_id"],
        url=url,
        html=row["html"],
        capture_title=row["capture_title"],
        attempts=row["attempts"],
    )


def types_in_use(conn: sqlite3.Connection) -> list[str]:
    return [r["name"] for r in conn.execute("SELECT name FROM type ORDER BY name")]


def _store_summary(
    svc: "Bookmarks", claim: Claim, summary: Summary, *, model: str, truncated: bool
) -> None:
    conn = svc.conn
    with transaction(conn):
        conn.execute("INSERT OR IGNORE INTO type (name) VALUES (?)", (summary.type,))
        conn.execute(
            "UPDATE item SET title = ?, type = ?, summary = ?, entities = ?, "
            "status = 'summarised', failure_reason = NULL, "
            "prov_cli = ?, prov_model = ?, prov_prompt_hash = ?, prov_at = ?, "
            "prov_truncated = ? WHERE id = ?",
            (
                summary.title,
                summary.type,
                summary.summary,
                json.dumps(summary.entities),
                svc.summariser.name,
                model,
                svc.prompt.hash,
                to_iso(svc.clock.now()),
                int(truncated),
                claim.item_id,
            ),
        )
        conn.execute("DELETE FROM queue WHERE item_id = ?", (claim.item_id,))


def mark_failed(conn: sqlite3.Connection, item_id: int, reason: str) -> None:
    with transaction(conn):
        conn.execute(
            "UPDATE item SET status = 'failed', failure_reason = ? WHERE id = ?",
            (reason, item_id),
        )
        conn.execute("DELETE FROM queue WHERE item_id = ?", (item_id,))


class _Stop(Exception):
    """A systemic failure: stop the run, count nothing."""


def _release(conn: sqlite3.Connection, item_id: int) -> None:
    conn.execute("UPDATE queue SET claimed_at = NULL WHERE item_id = ?", (item_id,))


def _retry_or_fail(svc: "Bookmarks", claim: Claim, reason: str) -> str:
    """A transient failure costs one attempt; the last attempt fails the item."""
    attempts = claim.attempts + 1
    if attempts >= MAX_ATTEMPTS:
        mark_failed(svc.conn, claim.item_id, f"{reason} (after {attempts} attempts)")
        return "failed"
    svc.conn.execute(
        "UPDATE queue SET attempts = ?, claimed_at = NULL WHERE item_id = ?",
        (attempts, claim.item_id),
    )
    return "retry"


def _summarise(svc: "Bookmarks", claim: Claim, acquired: Acquired) -> str:
    source, truncated = cap_source(acquired.text, svc.settings.source_cap_chars)
    request = build_request(
        svc.prompt,
        url=claim.url,
        title=acquired.title or claim.capture_title,
        description=acquired.description,
        types=types_in_use(svc.conn),
        source=source,
        truncated=truncated,
        model=svc.settings.summariser_model,
        timeout=svc.settings.summariser_timeout,
    )
    try:
        result = svc.summariser.submit(request)
    except ProviderFailure as failure:
        if failure.failure_class in PAUSE_CLASSES:
            _release(svc.conn, claim.item_id)
            raise _Stop(f"{failure.failure_class}: {failure}") from None
        return _retry_or_fail(svc, claim, f"summariser {failure.failure_class}")
    try:
        reply = parse_reply(result.text)
    except InvalidReply:
        return _retry_or_fail(svc, claim, "summariser reply invalid")
    if isinstance(reply, Unreadable):
        mark_failed(svc.conn, claim.item_id, f"unreadable: {reply.reason}")
        return "failed"
    _store_summary(svc, claim, reply, model=result.model, truncated=truncated)
    return "summarised"


def process(svc: "Bookmarks", claim: Claim) -> str:
    """Handle one claimed item: 'summarised', 'failed' or 'retry'.

    Raises `_Stop` on a systemic failure, with the claim released and no
    attempt counted.
    """
    try:
        acquired = acquire(
            svc.fetcher,
            claim.url,
            claim.html,
            github_token=svc.settings.github_token,
        )
    except Unacquirable as failure:
        if failure.transient:
            return _retry_or_fail(svc, claim, failure.reason)
        mark_failed(svc.conn, claim.item_id, failure.reason)
        return "failed"
    return _summarise(svc, claim, acquired)


def run_drain(svc: "Bookmarks", *, limit: int | None = None) -> DrainReport:
    recover_stale(svc.conn)
    report = DrainReport()
    # One attempt per item per run: a retried item waits for the next drain.
    tried: set[int] = set()
    consecutive_retries = 0
    while limit is None or len(tried) < limit:
        claim = claim_next(svc.conn, to_iso(svc.clock.now()), exclude=tried)
        if claim is None:
            break
        tried.add(claim.item_id)
        try:
            outcome = process(svc, claim)
        except _Stop as stop:
            report.stopped = str(stop)
            break
        setattr(report, outcome, getattr(report, outcome) + 1)
        consecutive_retries = consecutive_retries + 1 if outcome == "retry" else 0
        if consecutive_retries >= BREAKER_THRESHOLD:
            report.stopped = (
                f"circuit breaker: {consecutive_retries} consecutive transient failures"
            )
            break
    return report
