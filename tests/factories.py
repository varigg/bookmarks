"""Record factories: put submissions and items into the store through the core."""

from datetime import UTC, datetime
from pathlib import Path

from bookmarks import db, store
from bookmarks.ingest.drain import Submission, get_submission
from bookmarks.service import Bookmarks
from bookmarks.store import Item


def item_at(service: Bookmarks, url: str) -> Item | None:
    return store.get_by_url(service.conn, url)


def submission_at(service: Bookmarks, url: str) -> Submission | None:
    return get_submission(service.conn, url)


def is_recent(stamp: str) -> bool:
    """A stored timestamp in the stored form, taken within the last minute."""
    moment = datetime.strptime(stamp, db.TIMESTAMP_FORMAT).replace(tzinfo=UTC)
    return 0 <= (datetime.now(UTC) - moment).total_seconds() < 60


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
    saved_at: str | None = None,
) -> Item:
    """Save and drain one item through the core with a scripted summary."""
    from tests.fakes import summary_json

    service.fetcher.page(url, fixture_text("article.html"))
    service.summariser.script(
        summary_json(title=title, type=type, summary=summary, entities=entities or [])
    )
    saved = service.save(url, note=note, saved_at=saved_at)
    service.drain()
    return item_at(service, saved.url)
