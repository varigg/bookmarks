"""Drain on the generic route: a pending item becomes summarised."""

import json

import pytest

from bookmarks.settings import Settings
from tests.factories import fixture_text
from tests.fakes import summary_json

URL = "https://example.com/local-first"
ARTICLE = fixture_text("article.html")
THIN = fixture_text("js_shell.html")


def test_save_with_html_and_thin_server_fetch_summarises_client_text(
    service, fetcher, summariser
):
    fetcher.page(URL, THIN)
    saved = service.save(URL, html=ARTICLE)

    report = service.drain()

    assert report.summarised == 1
    prompt = summariser.requests[0].user_prompt
    assert "Conflict-free Replicated Data Types" in prompt
    assert "enable JavaScript" not in prompt
    assert service.get_item(saved.item.id).status == "summarised"


def test_longer_server_fetch_wins_over_thin_client_html(service, fetcher, summariser):
    fetcher.page(URL, ARTICLE)
    service.save(URL, html=THIN)

    service.drain()

    assert "Conflict-free Replicated Data Types" in summariser.requests[0].user_prompt


def test_summarised_item_carries_summary_and_full_provenance(
    service, fetcher, summariser, clock
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
    saved = service.save(URL)
    clock.advance(minutes=10)

    service.drain()

    item = service.get_item(saved.item.id)
    assert item.title == "Local-first software"
    assert item.type == "article"
    assert item.summary == "Ink & Switch argue for local-first software."
    assert item.entities == ["Ink & Switch", "CRDT", "Automerge"]
    assert item.provenance.cli == "claude-cli"
    assert item.provenance.model == "claude-sonnet-5-5"
    assert item.provenance.prompt_hash == service.prompt.hash
    assert len(item.provenance.prompt_hash) == 12
    assert item.provenance.at == "2026-09-30T12:10:00Z"
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
    saved = service.save(URL)

    service.drain()

    prompt = summariser.requests[0].user_prompt
    assert "Cloud apps like Google Docs" in prompt
    assert "open problems in sync" not in prompt
    assert "truncated" in prompt
    assert service.get_item(saved.item.id).provenance.truncated is True


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
    saved = service.save(URL)

    service.drain()

    assert "Types in use: article, discussion, docs, media, product, repo" in (
        summariser.requests[0].user_prompt
    )
    assert service.get_item(saved.item.id).type == "paper"
    assert "paper" in service.list_types()


def test_unreadable_reply_marks_the_item_failed_with_the_reason(
    service, fetcher, summariser
):
    fetcher.page(URL, ARTICLE)
    summariser.script(json.dumps({"unreadable": "login wall"}))
    saved = service.save(URL)

    report = service.drain()

    item = service.get_item(saved.item.id)
    assert report.failed == 1
    assert item.status == "failed"
    assert item.failure_reason == "unreadable: login wall"
    assert item.summary is None


@pytest.mark.parametrize("reply", [summary_json(), json.dumps({"unreadable": "x"})])
def test_client_html_is_gone_once_the_item_leaves_pending(
    service, fetcher, summariser, reply
):
    fetcher.page(URL, ARTICLE)
    summariser.script(reply)
    saved = service.save(URL, html=ARTICLE)

    service.drain()

    row = service.conn.execute(
        "SELECT html FROM queue WHERE item_id = ?", (saved.item.id,)
    ).fetchone()
    assert row is None


def test_drain_takes_items_oldest_first_and_honours_limit(
    service, fetcher, summariser, clock
):
    for n in range(3):
        fetcher.page(f"{URL}/{n}", ARTICLE)
        service.save(f"{URL}/{n}")
        clock.advance(minutes=1)

    report = service.drain(limit=2)

    assert report.summarised == 2
    assert [r.user_prompt.splitlines()[0] for r in summariser.requests] == [
        f"URL: {URL}/0",
        f"URL: {URL}/1",
    ]
