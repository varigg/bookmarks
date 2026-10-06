"""Drain on the generic route: a pending submission becomes an item."""

import json

import pytest

from bookmarks.settings import Settings
from tests.factories import fixture_text, is_recent, item_at, submission_at
from tests.fakes import summary_json

URL = "https://example.com/local-first"
ARTICLE = fixture_text("article.html")
THIN = fixture_text("js_shell.html")


def test_save_with_html_and_thin_server_fetch_summarises_client_text(
    service, fetcher, summariser
):
    fetcher.page(URL, THIN)
    service.save(URL, html=ARTICLE)

    report = service.drain()

    assert report.summarised == 1
    prompt = summariser.requests[0].user_prompt
    assert "Conflict-free Replicated Data Types" in prompt
    assert "enable JavaScript" not in prompt
    assert item_at(service, URL) is not None


def test_longer_server_fetch_wins_over_thin_client_html(service, fetcher, summariser):
    fetcher.page(URL, ARTICLE)
    service.save(URL, html=THIN)

    service.drain()

    assert "Conflict-free Replicated Data Types" in summariser.requests[0].user_prompt


def test_summarised_item_carries_summary_and_full_provenance(
    service, fetcher, summariser
):
    fetcher.page(URL, ARTICLE)
    summariser.script(
        summary_json(
            title="Local-first software",
            type="article",
            summary="Ink & Switch argue for local-first software.",
            entities=["Ink & Switch", "CRDT", "Automerge", "crdt"],
        )
    )
    service.save(URL, note="for the reading group", saved_at="2026-09-30T12:00:00Z")

    service.drain()

    assert submission_at(service, URL) is None
    item = item_at(service, URL)
    assert item.domain == "example.com"
    assert item.note == "for the reading group"
    assert item.saved_at == "2026-09-30T12:00:00Z"
    assert item.title == "Local-first software"
    assert item.type == "article"
    assert item.summary == "Ink & Switch argue for local-first software."
    assert item.entities == ["Ink & Switch", "CRDT", "Automerge"]
    assert item.provenance.cli == "claude-cli"
    assert item.provenance.model == "claude-sonnet-5-5"
    assert item.provenance.prompt_hash == service.prompt.hash
    assert len(item.provenance.prompt_hash) == 12
    assert is_recent(item.provenance.at)
    assert item.provenance.truncated is False


def test_request_is_single_turn_with_the_configured_model(service, fetcher, summariser):
    fetcher.page(URL, ARTICLE)
    service.save(URL)

    service.drain()

    request = summariser.requests[0]
    assert request.model == "claude-sonnet-5-5"
    assert request.system_prompt == service.prompt.text


def test_source_over_the_cap_is_truncated_from_the_end(
    make_service, settings, fetcher, summariser
):
    service = make_service(
        settings=Settings(db_path=settings.db_path, source_cap_chars=400)
    )
    fetcher.page(URL, ARTICLE)
    service.save(URL)

    service.drain()

    prompt = summariser.requests[0].user_prompt
    assert "Cloud apps like Google Docs" in prompt
    assert "open problems in sync" not in prompt
    assert "truncated" in prompt
    assert item_at(service, URL).provenance.truncated is True


def test_the_note_never_reaches_the_summariser(service, fetcher, summariser):
    fetcher.page(URL, ARTICLE)
    service.save(URL, note="zebra-marker: recommended by Ana")

    service.drain()

    request = summariser.requests[0]
    assert "zebra-marker" not in request.user_prompt
    assert "zebra-marker" not in request.system_prompt


def test_types_in_use_are_offered_and_a_new_type_is_adopted(
    service, fetcher, summariser
):
    fetcher.page(URL, ARTICLE)
    summariser.script(summary_json(type="Paper"))
    service.save(URL)

    service.drain()

    assert "Types in use: article, discussion, docs, media, product, repo" in (
        summariser.requests[0].user_prompt
    )
    assert item_at(service, URL).type == "paper"
    assert "paper" in service.list_types()


def test_unreadable_reply_marks_the_submission_failed_with_the_reason(
    service, fetcher, summariser
):
    fetcher.page(URL, ARTICLE)
    summariser.script(json.dumps({"unreadable": "login wall"}))
    service.save(URL)

    report = service.drain()

    submission = submission_at(service, URL)
    assert report.failed == 1
    assert submission.status == "failed"
    assert submission.failure_reason == "unreadable: login wall"
    assert item_at(service, URL) is None


@pytest.mark.parametrize("reply", [summary_json(), json.dumps({"unreadable": "x"})])
def test_client_html_is_gone_once_the_submission_leaves_pending(
    service, fetcher, summariser, reply
):
    fetcher.page(URL, ARTICLE)
    summariser.script(reply)
    service.save(URL, html=ARTICLE)

    service.drain()

    row = service.conn.execute(
        "SELECT html FROM submission WHERE url = ?", (URL,)
    ).fetchone()
    assert row is None or row["html"] is None


def test_drain_takes_submissions_oldest_first_and_honours_limit(
    service, fetcher, summariser
):
    for n in range(3):
        fetcher.page(f"{URL}/{n}", ARTICLE)
        service.save(f"{URL}/{n}", saved_at=f"2026-09-30T12:0{n}:00Z")

    report = service.drain(limit=2)

    assert report.summarised == 2
    assert [r.user_prompt.splitlines()[0] for r in summariser.requests] == [
        f"URL: {URL}/0",
        f"URL: {URL}/1",
    ]
