"""The drain: claim pending submissions one at a time and run their stages.

A mechanism: it decides when work runs and when a run stops, never what an
outcome means; it reports every outcome to `lifecycle`.

The claim protocol (atomic `UPDATE ... RETURNING`, stale-claim recovery at
startup, concurrency of one) is adapted from adventure-library
`src/adventure_library/jobs.py` and `worker.py` at commit b264b17.
"""

import sqlite3
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bookmarks import store
from bookmarks.db import now_iso
from bookmarks.ingest import lifecycle
from bookmarks.ingest.fetch import Unretrievable
from bookmarks.ingest.lifecycle import Claim
from bookmarks.ingest.llm.provider import PAUSE_CLASSES, ProviderFailure
from bookmarks.ingest.retrieve import Retrieved, retrieve
from bookmarks.ingest.summarise import build_request, cap_source

if TYPE_CHECKING:
    from bookmarks.service import Bookmarks


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


class _Stop(Exception):
    """A systemic failure: stop the run, count nothing."""


def _release(conn: sqlite3.Connection, submission_id: int) -> None:
    conn.execute(
        "UPDATE submission SET claimed_at = NULL WHERE id = ?", (submission_id,)
    )


def _summarise(svc: "Bookmarks", claim: Claim, retrieved: Retrieved) -> str:
    source, truncated = cap_source(retrieved.text, svc.settings.source_cap_chars)
    request = build_request(
        svc.prompt,
        url=claim.url,
        title=retrieved.title or claim.capture_title,
        description=retrieved.description,
        types=store.types_in_use(svc.conn),
        source=source,
        truncated=truncated,
    )
    try:
        result = svc.summariser.submit(request)
    except ProviderFailure as failure:
        if failure.failure_class in PAUSE_CLASSES:
            _release(svc.conn, claim.submission_id)
            raise _Stop(f"{failure.failure_class}: {failure}") from None
        return lifecycle.summariser_failed(svc, claim, failure.failure_class)
    return lifecycle.replied(
        svc, claim, result.text, model=result.model, truncated=truncated
    )


def process(svc: "Bookmarks", claim: Claim) -> str:
    """Handle one claimed submission: 'summarised', 'failed' or 'retry'.

    Raises `_Stop` on a systemic failure, with the claim released and no
    attempt counted.
    """
    try:
        retrieved = retrieve(
            svc.fetcher,
            claim.url,
            claim.html,
            github_token=svc.settings.github_token,
        )
    except Unretrievable as failure:
        return lifecycle.retrieving_failed(svc, claim, failure)
    return _summarise(svc, claim, retrieved)


def run_drain(svc: "Bookmarks", *, limit: int | None = None) -> DrainReport:
    recover_stale(svc.conn)
    report = DrainReport()
    # One attempt per submission per run: a retry waits for the next drain.
    tried: set[int] = set()
    consecutive_retries = 0
    while limit is None or len(tried) < limit:
        claim = claim_next(svc.conn, now_iso(), exclude=tried)
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
