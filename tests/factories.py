"""Record factories: put items into the store through the core."""

from pathlib import Path

from bookmarks.service import Bookmarks
from bookmarks.store import Item

_counter = 0


def saved_item(service: Bookmarks, url: str | None = None, **fields) -> Item:
    global _counter
    _counter += 1
    url = url or f"https://example.com/article-{_counter}"
    return service.save(url, **fields).item


FIXTURES = Path(__file__).parent / "fixtures"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def summarised_item(
    service: Bookmarks,
    *,
    url: str,
    title: str,
    summary: str,
    entities: list[str] | None = None,
    type: str = "article",
    note: str | None = None,
) -> Item:
    """Save and drain one item through the core with a scripted summary."""
    from tests.fakes import summary_json

    service.fetcher.page(url, fixture_text("article.html"))
    service.summariser.script(
        summary_json(title=title, type=type, summary=summary, entities=entities or [])
    )
    item = service.save(url, note=note).item
    service.drain()
    return service.get_item(item.id)
