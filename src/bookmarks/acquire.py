"""Acquisition: turn a queued item into source text at drain time.

Routes are chosen by URL rule, never by type. A route either returns source
text or raises `Unacquirable`, saying whether the failure is transient
(retry on a later drain) or permanent (fail the item now).
"""

import re
from dataclasses import dataclass

from bookmarks.extract import Extracted, extract
from bookmarks.fetch import Fetcher, FetchError, HttpResponse
from bookmarks.github import GitHubFailure, fetch_readme, repo_of


@dataclass(frozen=True)
class Acquired:
    text: str
    title: str | None
    description: str | None


class Unacquirable(Exception):
    def __init__(self, reason: str, *, transient: bool) -> None:
        super().__init__(reason)
        self.reason = reason
        self.transient = transient


def classify_status(status: int) -> tuple[str, bool] | None:
    """(reason, transient) for a non-success HTTP status, None for success."""
    if 200 <= status < 300:
        return None
    if status in (404, 410):
        return f"not found (HTTP {status})", False
    if status == 429 or status >= 500:
        return f"server error (HTTP {status})", True
    return f"HTTP {status}", False


# A short page whose text is mostly one of these is a wall, not content.
_WALL_TEXT_LIMIT = 1500
_WALLS = (
    (
        "JavaScript required",
        re.compile(
            r"(enable|turn on|requires?) javascript|javascript (is )?(disabled|required)",
            re.IGNORECASE,
        ),
    ),
    (
        "login wall",
        re.compile(
            r"(log|sign) ?in to (continue|view|see|read)|please (log|sign) ?in"
            r"|you must be (logged|signed) in",
            re.IGNORECASE,
        ),
    ),
    (
        "cookie wall",
        re.compile(
            r"(accept|consent to) (all )?cookies to (continue|view|access)"
            r"|before you continue",
            re.IGNORECASE,
        ),
    ),
)


def detect_wall(text: str) -> str | None:
    if len(text) > _WALL_TEXT_LIMIT:
        return None
    for name, pattern in _WALLS:
        if pattern.search(text):
            return name
    return None


def _source_text(extracted: Extracted) -> str:
    return extracted.text or extracted.description or ""


def _no_text_failure(server: HttpResponse | FetchError | None) -> Unacquirable:
    if isinstance(server, FetchError):
        return Unacquirable(str(server), transient=True)
    if server is not None:
        classified = classify_status(server.status)
        if classified is not None:
            reason, transient = classified
            return Unacquirable(reason, transient=transient)
    return Unacquirable("no readable content", transient=False)


def acquire_generic(fetcher: Fetcher, url: str, client_html: str | None) -> Acquired:
    """Server fetch and client html go through the same extractor; the longer
    source text wins."""
    server: HttpResponse | FetchError
    try:
        server = fetcher.get(url)
    except FetchError as exc:
        server = exc
    server_html = (
        server.text
        if isinstance(server, HttpResponse) and classify_status(server.status) is None
        else None
    )
    from_server = extract(server_html, url)
    from_client = extract(client_html, url)
    winner, other = (
        (from_client, from_server)
        if len(_source_text(from_client)) > len(_source_text(from_server))
        else (from_server, from_client)
    )
    text = _source_text(winner)
    if not text.strip():
        raise _no_text_failure(server)
    wall = detect_wall(text)
    if wall is not None:
        server_failure = _no_text_failure(server)
        if server_failure.transient:
            # The server may yet answer with the real page on a later drain.
            raise server_failure
        raise Unacquirable(wall, transient=False)
    return Acquired(
        text=text,
        title=winner.title or other.title,
        description=winner.description or other.description,
    )


def acquire_github(
    fetcher: Fetcher, url: str, client_html: str | None, token: str | None
) -> Acquired:
    """The API README wins over any client html; a repo without a README
    falls back to the generic route."""
    repo = repo_of(url)
    assert repo is not None
    try:
        readme = fetch_readme(fetcher, repo, token)
    except GitHubFailure as failure:
        raise Unacquirable(failure.reason, transient=failure.transient) from None
    if not readme.text:
        return acquire_generic(fetcher, url, client_html)
    return Acquired(
        text=readme.text, title=readme.full_name, description=readme.description
    )


def acquire(
    fetcher: Fetcher,
    url: str,
    client_html: str | None,
    *,
    github_token: str | None = None,
) -> Acquired:
    """Pick the acquisition route by URL rule."""
    if repo_of(url) is not None:
        return acquire_github(fetcher, url, client_html, github_token)
    return acquire_generic(fetcher, url, client_html)
