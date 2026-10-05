"""Acquisition: turn a queued item into source text at drain time.

Routes are chosen by URL rule, never by type. A route either returns source
text or raises `Unacquirable`, saying whether the failure is transient
(retry on a later drain) or permanent (fail the item now).
"""

from dataclasses import dataclass

from bookmarks.ingest.extract import Extracted, extract
from bookmarks.ingest.fetch import Fetcher, FetchError, HttpResponse, Unacquirable
from bookmarks.ingest.github import fetch_readme, repo_of


@dataclass(frozen=True)
class Acquired:
    text: str
    title: str | None
    description: str | None


def classify_status(status: int) -> tuple[str, bool] | None:
    """(reason, transient) for a non-success HTTP status, None for success."""
    if 200 <= status < 300:
        return None
    if status in (404, 410):
        return f"not found (HTTP {status})", False
    if status == 429 or status >= 500:
        return f"server error (HTTP {status})", True
    return f"HTTP {status}", False


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
    readme = fetch_readme(fetcher, repo, token)
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
