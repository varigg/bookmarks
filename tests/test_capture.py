"""Saving a URL through the core."""

import pytest

from bookmarks.urls import InvalidUrl, normalise_url
from tests.factories import item_at, submission_at, summarised_item


def test_save_creates_a_pending_submission_and_no_item(service):
    result = service.save("https://example.com/post", title="A Post", note="for later")

    assert result.outcome == "saved"
    assert result.message == "Saved"
    assert result.note_added is True
    assert result.status == "pending"
    assert result.saved_at == "2026-09-30T12:00:00Z"
    submission = submission_at(service, "https://example.com/post")
    assert submission.status == "pending"
    assert submission.note == "for later"
    assert submission.saved_at == "2026-09-30T12:00:00Z"
    assert item_at(service, "https://example.com/post") is None


def test_tracking_params_and_fragment_are_stripped_before_storing(service):
    result = service.save(
        "https://example.com/a?id=7&utm_source=news&fbclid=xyz&utm_medium=mail#top"
    )

    assert result.url == "https://example.com/a?id=7"


def test_resave_of_same_normalised_url_is_already_saved(service, clock):
    first = service.save("https://example.com/a?utm_campaign=x")
    clock.advance(days=3)

    again = service.save("https://example.com/a#comments")

    assert again.outcome == "already_saved"
    assert again.message == "Already saved on 2026-09-30"
    assert again.status == "pending"
    assert again.url == first.url
    count = service.conn.execute("SELECT count(*) FROM submission").fetchone()[0]
    assert count == 1


def test_resave_of_a_summarised_url_is_already_saved(service):
    summarised_item(
        service, url="https://example.com/a", title="A", summary="An article."
    )

    again = service.save("https://example.com/a", note="again")

    assert again.outcome == "already_saved"
    assert again.status == "summarised"
    assert again.message == "Already saved on 2026-09-30; note not added"
    assert submission_at(service, "https://example.com/a") is None


def test_note_on_a_duplicate_save_is_reported_not_added(service):
    service.save("https://example.com/a", note="original")

    again = service.save("https://example.com/a", note="second thoughts")

    assert again.note_added is False
    assert again.message == "Already saved on 2026-09-30; note not added"
    assert submission_at(service, again.url).note == "original"


def test_blank_note_is_no_note(service):
    result = service.save("https://example.com/a", note="   ")

    assert result.note_added is False
    assert submission_at(service, result.url).note is None


@pytest.mark.parametrize("url", ["ftp://example.com/x", "not a url", "https://"])
def test_non_http_urls_are_rejected(service, url):
    with pytest.raises(InvalidUrl):
        service.save(url)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("https://Example.com/Path/?b=2&a=1", "https://Example.com/Path/?b=2&a=1"),
        ("https://example.com/?utm_x=1", "https://example.com/"),
        ("http://example.com/p?gclid=1&q=a%20b#f", "http://example.com/p?q=a%20b"),
        ("https://example.com/p?UTM_Source=x&keep", "https://example.com/p?keep"),
    ],
)
def test_normalise_url_keeps_everything_but_tracking_and_fragment(raw, expected):
    assert normalise_url(raw) == expected
