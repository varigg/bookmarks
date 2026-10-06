"""The submission lifecycle: what each stage outcome means for a submission.

Owns Submission, Stage and Status: the retry budget, which failures are
final, turning a summarised submission into an item, and re-saving a failed
URL. The drain runs stages; it reports each outcome here.
"""

import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bookmarks import store
from bookmarks.db import now_iso, transaction
from bookmarks.ingest.fetch import Unretrievable
from bookmarks.ingest.summarise import InvalidReply, Summary, Unreadable, parse_reply

if TYPE_CHECKING:
    from bookmarks.service import Bookmarks


@dataclass(frozen=True)
class Claim:
    submission_id: int
    url: str
    note: str | None
    saved_at: str
    html: str | None
    capture_title: str | None
    attempts: int


@dataclass(frozen=True)
class Submission:
    url: str
    note: str | None
    saved_at: str
    status: str
    failure_reason: str | None
    attempts: int


MAX_ATTEMPTS = 3


def get_submission(conn: sqlite3.Connection, url: str) -> Submission | None:
    row = conn.execute(
        "SELECT url, note, saved_at, status, failure_reason, attempts "
        "FROM submission WHERE url = ?",
        (url,),
    ).fetchone()
    return Submission(**row) if row is not None else None


def _store_summary(
    svc: "Bookmarks", claim: Claim, summary: Summary, *, model: str, truncated: bool
) -> None:
    conn = svc.conn
    with transaction(conn):
        store.insert_item(
            conn,
            url=claim.url,
            title=summary.title,
            type=summary.type,
            summary=summary.summary,
            entities=summary.entities,
            note=claim.note,
            saved_at=claim.saved_at,
            provenance=store.Provenance(
                cli=svc.summariser.name,
                model=model,
                prompt_hash=svc.prompt.hash,
                at=now_iso(),
                truncated=truncated,
            ),
        )
        conn.execute("DELETE FROM submission WHERE id = ?", (claim.submission_id,))


def mark_failed(conn: sqlite3.Connection, submission_id: int, reason: str) -> None:
    """The capture html goes with the failure; a re-save sends it afresh."""
    conn.execute(
        "UPDATE submission SET status = 'failed', failure_reason = ?, html = NULL, "
        "claimed_at = NULL WHERE id = ?",
        (reason, submission_id),
    )


def _retry_or_fail(svc: "Bookmarks", claim: Claim, reason: str) -> str:
    """A transient failure costs one attempt; the last attempt fails it."""
    attempts = claim.attempts + 1
    if attempts >= MAX_ATTEMPTS:
        mark_failed(
            svc.conn, claim.submission_id, f"{reason} (after {attempts} attempts)"
        )
        return "failed"
    svc.conn.execute(
        "UPDATE submission SET attempts = ?, claimed_at = NULL WHERE id = ?",
        (attempts, claim.submission_id),
    )
    return "retry"


def classify_status(status: int) -> tuple[str, bool] | None:
    """(reason, transient) for a non-success HTTP status, None for success."""
    if 200 <= status < 300:
        return None
    if status in (404, 410):
        return f"not found (HTTP {status})", False
    if status == 429 or status >= 500:
        return f"server error (HTTP {status})", True
    return f"HTTP {status}", False


def submit(
    conn: sqlite3.Connection,
    url: str,
    *,
    note: str | None,
    saved_at: str,
    html: str | None,
    title: str | None,
) -> None:
    conn.execute(
        "INSERT INTO submission "
        "(url, note, saved_at, html, capture_title, enqueued_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (url, note, saved_at, html, title, saved_at),
    )


def requeue(
    conn: sqlite3.Connection, url: str, *, html: str | None, title: str | None
) -> None:
    """A failed submission gets another chance with whatever page is sent
    now; its original note and saved time are kept."""
    conn.execute(
        "UPDATE submission SET status = 'pending', failure_reason = NULL, "
        "html = ?, capture_title = ?, attempts = 0, claimed_at = NULL, "
        "enqueued_at = ? WHERE url = ?",
        (html, title, now_iso(), url),
    )


def retrieving_failed(svc: "Bookmarks", claim: Claim, failure: Unretrievable) -> str:
    if failure.transient:
        return _retry_or_fail(svc, claim, failure.reason)
    mark_failed(svc.conn, claim.submission_id, failure.reason)
    return "failed"


def summariser_failed(svc: "Bookmarks", claim: Claim, failure_class: str) -> str:
    """Any failure the drain does not pause on costs an attempt."""
    return _retry_or_fail(svc, claim, f"summariser {failure_class}")


def replied(
    svc: "Bookmarks", claim: Claim, text: str, *, model: str, truncated: bool
) -> str:
    """An invalid reply costs an attempt; an unreadable page fails for good;
    a summary becomes an item."""
    try:
        reply = parse_reply(text)
    except InvalidReply:
        return _retry_or_fail(svc, claim, "summariser reply invalid")
    if isinstance(reply, Unreadable):
        mark_failed(svc.conn, claim.submission_id, f"unreadable: {reply.reason}")
        return "failed"
    _store_summary(svc, claim, reply, model=model, truncated=truncated)
    return "summarised"
