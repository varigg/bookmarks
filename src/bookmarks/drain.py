"""The drain: claim queued items one at a time and summarise them.

The claim protocol (atomic `UPDATE ... RETURNING`, stale-claim recovery at
startup, concurrency of one) is adapted from adventure-library
`src/adventure_library/jobs.py` and `worker.py` at commit b264b17.
"""

import json
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bookmarks.acquire import acquire_generic
from bookmarks.clock import to_iso
from bookmarks.summarise import (
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


@dataclass
class DrainReport:
    summarised: int = 0
    failed: int = 0


def recover_stale(conn: sqlite3.Connection) -> None:
    """Concurrency of one: any claim still held at startup is a dead run's."""
    conn.execute("UPDATE queue SET claimed_at = NULL WHERE claimed_at IS NOT NULL")


def claim_next(conn: sqlite3.Connection, now: str) -> Claim | None:
    row = conn.execute(
        "UPDATE queue SET claimed_at = ? "
        "WHERE item_id = (SELECT item_id FROM queue WHERE claimed_at IS NULL "
        "                 ORDER BY enqueued_at, item_id LIMIT 1) "
        "AND claimed_at IS NULL "
        "RETURNING item_id, html, capture_title, attempts",
        (now,),
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
    conn.execute("BEGIN IMMEDIATE")
    try:
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
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def mark_failed(conn: sqlite3.Connection, item_id: int, reason: str) -> None:
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "UPDATE item SET status = 'failed', failure_reason = ? WHERE id = ?",
            (reason, item_id),
        )
        conn.execute("DELETE FROM queue WHERE item_id = ?", (item_id,))
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def process(svc: "Bookmarks", claim: Claim) -> bool:
    """Summarise one claimed item. Returns True when it ended summarised."""
    acquired = acquire_generic(svc.fetcher, claim.url, claim.html)
    if not acquired.text.strip():
        mark_failed(svc.conn, claim.item_id, "no readable content")
        return False
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
    result = svc.summariser.submit(request)
    reply = parse_reply(result.text)
    if isinstance(reply, Unreadable):
        mark_failed(svc.conn, claim.item_id, f"unreadable: {reply.reason}")
        return False
    _store_summary(svc, claim, reply, model=result.model, truncated=truncated)
    return True


def run_drain(svc: "Bookmarks", *, limit: int | None = None) -> DrainReport:
    recover_stale(svc.conn)
    report = DrainReport()
    while limit is None or report.summarised + report.failed < limit:
        claim = claim_next(svc.conn, to_iso(svc.clock.now()))
        if claim is None:
            break
        if process(svc, claim):
            report.summarised += 1
        else:
            report.failed += 1
    return report
