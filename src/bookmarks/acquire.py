"""Acquisition: turn a queued item into source text at drain time.

Routes are chosen by URL rule, never by type.
"""

from dataclasses import dataclass

from bookmarks.extract import Extracted, extract
from bookmarks.fetch import Fetcher, FetchError


@dataclass(frozen=True)
class Acquired:
    text: str
    title: str | None
    description: str | None


def _source_text(extracted: Extracted) -> str:
    return extracted.text or extracted.description or ""


def acquire_generic(fetcher: Fetcher, url: str, client_html: str | None) -> Acquired:
    """Server fetch and client html go through the same extractor; the longer
    source text wins."""
    try:
        response = fetcher.get(url)
        server_html = response.text if 200 <= response.status < 300 else None
    except FetchError:
        server_html = None
    server = extract(server_html, url)
    client = extract(client_html, url)
    winner, other = (
        (client, server)
        if len(_source_text(client)) > len(_source_text(server))
        else (server, client)
    )
    return Acquired(
        text=_source_text(winner),
        title=winner.title or other.title,
        description=winner.description or other.description,
    )
