"""Import the old bookmarks app's data file as submissions (#33).

The file is JavaScript, `const bookmarks = [ ... ];`: the array is JSON.
Only each record's URL and `dateAdded` come across; the old titles,
descriptions and tags were written by a pipeline that had been failing
(docs/research/content-acquisition.md), so every URL is summarised fresh.
"""

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bookmarks.db import TIMESTAMP_FORMAT

if TYPE_CHECKING:
    from bookmarks.service import Bookmarks


@dataclass(frozen=True)
class LegacyBookmark:
    url: str
    saved_at: str


def parse(text: str) -> list[LegacyBookmark]:
    """The bookmarks in the file's leading JSON array; whatever precedes the
    array and follows it (`;`) is ignored. Raises `ValueError` if malformed."""
    start = text.find("[")
    if start < 0:
        raise ValueError("no JSON array in the legacy file")
    records, _ = json.JSONDecoder().raw_decode(text, start)
    return [
        LegacyBookmark(
            url=r["url"],
            saved_at=datetime.fromisoformat(r["dateAdded"])
            .astimezone(UTC)
            .strftime(TIMESTAMP_FORMAT),
        )
        for r in records
    ]


def import_legacy(svc: "Bookmarks", bookmarks: list[LegacyBookmark]) -> Counter:
    """Save each bookmark at its original time; counts by save outcome.

    Saving applies the duplicate rule, so a second import changes nothing."""
    return Counter(svc.save(b.url, saved_at=b.saved_at).outcome for b in bookmarks)
