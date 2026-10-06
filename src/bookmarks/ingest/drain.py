"""The drain: claim pending submissions one at a time and summarise them.

The claim protocol (atomic `UPDATE ... RETURNING`, stale-claim recovery at
startup, concurrency of one) is adapted from adventure-library
`src/adventure_library/jobs.py` and `worker.py` at commit b264b17.
"""

import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bookmarks import store
from bookmarks.clock import to_iso
from bookmarks.db import transaction
from bookmarks.ingest.acquire import Acquired, acquire
from bookmarks.ingest.fetch import Unacquirable
from bookmarks.ingest.llm.provider import PAUSE_CLASSES, ProviderFailure
from bookmarks.ingest.summarise import (
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
# Copied from adventure-library worker.py (b264b17): stop after this many
# consecutive failures, so an unrecognised outage costs a few items one
# attempt each rather than burning every submission's retry budget.
BREAKER_THRESHOLD = 5


@dataclass
class DrainReport:
    summarised: int = 0
    failed: int = 0
    retry: int = 0
    stopped: str | None = None


def recover_stale(conn: sqlite3.Connection) -> None:
    """Concurrency of one: any claim still held at startup is a dead run's."""
    conn.execute("UPDATE submission SET claimed_at = NULL WHERE claimed_at IS NOT NULL")


def claim_next(
    conn: sqlite3.Connection, now: str, *, exclude: set[int] = frozenset()
) -> Claim | None:
    skip = ",".join("?" * len(exclude))
    row = conn.execute(
        "UPDATE submission SET claimed_at = ? "
        "WHERE id = (SELECT id FROM submission "
        "            WHERE status = 'pending' AND claimed_at IS NULL "
        f"           AND id NOT IN ({skip}) "
        "            ORDER BY enqueued_at, id LIMIT 1) "
        "AND claimed_at IS NULL "
        "RETURNING id, url, note, saved_at, html, capture_title, attempts",
        (now, *exclude),
    ).fetchone()
    if row is None:
        return None
    return Claim(
        submission_id=row["id"],
        url=row["url"],
        note=row["note"],
        saved_at=row["saved_at"],
        html=row["html"],
        capture_title=row["capture_title"],
        attempts=row["attempts"],
    )


def get_submission(conn: sqlite3.Connection, url: str) -> Submission | None:
    row = conn.execute(
        "SELECT url, note, saved_at, status, failure_reason, attempts "
        "FROM submission WHERE url = ?",
        (url,),
    ).fetchone()
    return Submission(**row) if row is not None else None


def types_in_use(conn: sqlite3.Connection) -> list[str]:
    return [r["name"] for r in conn.execute("SELECT name FROM type ORDER BY name")]


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
                at=to_iso(svc.clock.now()),
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


class _Stop(Exception):
    """A systemic failure: stop the run, count nothing."""


def _release(conn: sqlite3.Connection, submission_id: int) -> None:
    conn.execute(
        "UPDATE submission SET claimed_at = NULL WHERE id = ?", (submission_id,)
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
            _release(svc.conn, claim.submission_id)
            raise _Stop(f"{failure.failure_class}: {failure}") from None
        return _retry_or_fail(svc, claim, f"summariser {failure.failure_class}")
    try:
        reply = parse_reply(result.text)
    except InvalidReply:
        return _retry_or_fail(svc, claim, "summariser reply invalid")
    if isinstance(reply, Unreadable):
        mark_failed(svc.conn, claim.submission_id, f"unreadable: {reply.reason}")
        return "failed"
    _store_summary(svc, claim, reply, model=result.model, truncated=truncated)
    return "summarised"


def process(svc: "Bookmarks", claim: Claim) -> str:
    """Handle one claimed submission: 'summarised', 'failed' or 'retry'.

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
        mark_failed(svc.conn, claim.submission_id, failure.reason)
        return "failed"
    return _summarise(svc, claim, acquired)


def run_drain(svc: "Bookmarks", *, limit: int | None = None) -> DrainReport:
    recover_stale(svc.conn)
    report = DrainReport()
    # One attempt per submission per run: a retry waits for the next drain.
    tried: set[int] = set()
    consecutive_retries = 0
    while limit is None or len(tried) < limit:
        claim = claim_next(svc.conn, to_iso(svc.clock.now()), exclude=tried)
        if claim is None:
            break
        tried.add(claim.submission_id)
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
