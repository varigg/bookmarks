"""Record factories: put items into the store through the core."""

from bookmarks.service import Bookmarks
from bookmarks.store import Item

_counter = 0


def saved_item(service: Bookmarks, url: str | None = None, **fields) -> Item:
    global _counter
    _counter += 1
    url = url or f"https://example.com/article-{_counter}"
    return service.save(url, **fields).item
