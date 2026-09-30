"""Readable-text extraction: a pure function of HTML.

Both the server fetch and the client html go through `extract`, so the
choice between them compares like with like.
"""

from dataclasses import dataclass

import trafilatura


@dataclass(frozen=True)
class Extracted:
    title: str | None
    description: str | None
    text: str

    @property
    def length(self) -> int:
        return len(self.text)


def _clean(text: str | None) -> str | None:
    return (text or "").strip() or None


def extract(html: str | None, url: str | None = None) -> Extracted:
    if not html or not html.strip():
        return Extracted(title=None, description=None, text="")
    text = trafilatura.extract(
        html,
        url=url,
        include_comments=True,
        include_tables=True,
        favor_recall=True,
    )
    metadata = trafilatura.extract_metadata(html, default_url=url)
    title = _clean(metadata.title) if metadata else None
    description = _clean(metadata.description) if metadata else None
    return Extracted(title=title, description=description, text=(text or "").strip())
