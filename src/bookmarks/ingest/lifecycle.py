"""The submission lifecycle: what each stage outcome means for a submission.

Owns Submission, Stage and Status: the retry budget, which failures are
final, turning a summarised submission into an item, and re-saving a failed
URL. The drain runs stages; it reports each outcome here.
"""

import dataclasses
import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

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
    source_text: str | None
    source_title: str | None
    source_description: str | None


@dataclass(frozen=True)
class Submission:
    url: str
    note: str | None
    saved_at: str
    status: str
    failure_reason: str | None
    attempts: int


# The columns a Submission is read from: its fields, in order.
_SUBMISSION_COLUMNS = ", ".join(f.name for f in dataclasses.fields(Submission))


# Per stage: a stage that succeeds resets the count for the next one.
MAX_ATTEMPTS = 3


def stage_of(claim: Claim) -> Literal["retrieving", "summarising"]:
    return "retrieving" if claim.source_text is None else "summarising"


def get_submission(conn: sqlite3.Connection, url: str) -> Submission | None:
    row = conn.execute(
        f"SELECT {_SUBMISSION_COLUMNS} FROM submission WHERE url = ?",
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
    """The capture html and source text go with the failure; a re-save
    retrieves afresh."""
    conn.execute(
        "UPDATE submission SET status = 'failed', failure_reason = ?, html = NULL, "
        "source_text = NULL, source_title = NULL, source_description = NULL, "
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


def retrieved(
    conn: sqlite3.Connection,
    claim: Claim,
    *,
    text: str,
    title: str | None,
    description: str | None,
) -> Claim:
    """Keep the source text in place of the capture html; summarising starts
    with a fresh retry budget."""
    conn.execute(
        "UPDATE submission SET source_text = ?, source_title = ?, "
        "source_description = ?, html = NULL, attempts = 0 WHERE id = ?",
        (text, title, description, claim.submission_id),
    )
    return dataclasses.replace(
        claim,
        html=None,
        attempts=0,
        source_text=text,
        source_title=title,
        source_description=description,
    )


def retrieving_failed(svc: "Bookmarks", claim: Claim, failure: Unretrievable) -> str:
    reason = f"retrieving: {failure.reason}"
    if failure.transient:
        return _retry_or_fail(svc, claim, reason)
    mark_failed(svc.conn, claim.submission_id, reason)
    return "failed"


def summariser_failed(svc: "Bookmarks", claim: Claim, failure_class: str) -> str:
    """Any failure the drain does not pause on costs an attempt."""
    return _retry_or_fail(svc, claim, f"summarising: {failure_class}")


def replied(
    svc: "Bookmarks", claim: Claim, text: str, *, model: str, truncated: bool
) -> str:
    """An invalid reply costs an attempt; an unreadable page fails for good;
    a summary becomes an item."""
    try:
        reply = parse_reply(text)
    except InvalidReply:
        return _retry_or_fail(svc, claim, "summarising: reply invalid")
    if isinstance(reply, Unreadable):
        reason = f"summarising: unreadable: {reply.reason}"
        mark_failed(svc.conn, claim.submission_id, reason)
        return "failed"
    _store_summary(svc, claim, reply, model=model, truncated=truncated)
    return "summarised"


def newest_submissions(
    conn: sqlite3.Connection, status: str | None, limit: int
) -> list[Submission]:
    """Pending and failed submissions, newest saved first; `status` narrows."""
    rows = conn.execute(
        f"SELECT {_SUBMISSION_COLUMNS} FROM submission WHERE ? IS NULL OR status = ? "
        "ORDER BY saved_at DESC, id DESC LIMIT ?",
        (status, status, limit),
    )
    return [Submission(**r) for r in rows]


def submission_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """How many submissions are pending and how many failed."""
    counts = {"pending": 0, "failed": 0}
    for row in conn.execute("SELECT status, COUNT(*) FROM submission GROUP BY status"):
        counts[row[0]] = row[1]
    return counts


def oldest_pending(conn: sqlite3.Connection) -> str | None:
    """Since when the longest-waiting pending submission has been owed a drain."""
    return conn.execute(
        "SELECT MIN(enqueued_at) FROM submission WHERE status = 'pending'"
    ).fetchone()[0]
