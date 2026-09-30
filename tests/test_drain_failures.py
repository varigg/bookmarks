"""Drain failure classes, retries, the circuit breaker, and re-queue on re-save."""

import json

import pytest

from bookmarks.fetch import FetchError, HttpResponse
from bookmarks.llm.provider import ProviderFailure
from tests.factories import fixture_text
from tests.fakes import summary_json

URL = "https://example.com/post"
ARTICLE = fixture_text("article.html")
JS_SHELL = fixture_text("js_shell.html")
LOGIN_WALL = """<html><head><title>Members</title></head><body>
<main><h1>Members only</h1><p>Please log in to continue reading this story.</p>
</main></body></html>"""
COOKIE_WALL = """<html><head><title>Consent</title></head><body>
<main><p>Before you continue to our site, you must accept cookies to continue.</p>
</main></body></html>"""


def _drain_attempts(service, clock, n):
    for _ in range(n):
        service.drain()
        clock.advance(minutes=10)


@pytest.mark.parametrize(
    "server",
    [
        FetchError("timeout", "timed out"),
        HttpResponse(status=503, text="unavailable"),
    ],
)
def test_fetch_timeout_or_5xx_retries_then_fails_on_the_third(
    service, fetcher, clock, server
):
    fetcher.script(URL, server)
    saved = service.save(URL)

    report = service.drain()
    assert report.retry == 1
    assert service.get_item(saved.item.id).status == "pending"

    _drain_attempts(service, clock, 2)

    item = service.get_item(saved.item.id)
    assert item.status == "failed"
    assert "(after 3 attempts)" in item.failure_reason


def test_malformed_reply_counts_an_attempt(service, fetcher, summariser, clock):
    fetcher.page(URL, ARTICLE)
    summariser.script("Sure! Here is the summary you asked for.")
    saved = service.save(URL)

    service.drain()
    assert service.get_item(saved.item.id).status == "pending"

    _drain_attempts(service, clock, 2)
    item = service.get_item(saved.item.id)
    assert item.status == "failed"
    assert item.failure_reason.startswith("summariser reply invalid")


def test_transient_failure_then_success_summarises(service, fetcher, summariser):
    fetcher.page(URL, ARTICLE)
    summariser.script(
        ProviderFailure("timeout", "claude -p exceeded 300s", retryable=True),
        summary_json(),
    )
    saved = service.save(URL)

    service.drain()
    service.drain()

    assert service.get_item(saved.item.id).status == "summarised"


def test_a_retried_item_waits_for_the_next_drain(service, fetcher, summariser):
    fetcher.script(URL, FetchError("timeout", "timed out"))
    service.save(URL)

    report = service.drain()

    assert report.retry == 1
    assert len(fetcher.requests) == 1


def test_404_fails_immediately_with_a_reason(service, fetcher, summariser):
    fetcher.page(URL, "gone", status=404)
    saved = service.save(URL)

    service.drain()

    item = service.get_item(saved.item.id)
    assert item.status == "failed"
    assert item.failure_reason == "not found (HTTP 404)"
    assert summariser.requests == []


@pytest.mark.parametrize(
    "html,reason",
    [
        (JS_SHELL, "JavaScript required"),
        (LOGIN_WALL, "login wall"),
        (COOKIE_WALL, "cookie wall"),
    ],
)
def test_detected_walls_fail_immediately(service, fetcher, summariser, html, reason):
    fetcher.page(URL, html)
    saved = service.save(URL)

    service.drain()

    item = service.get_item(saved.item.id)
    assert item.status == "failed"
    assert item.failure_reason == reason
    assert summariser.requests == []


def test_page_with_no_readable_text_fails_immediately(service, fetcher):
    fetcher.page(URL, "<html><body><div id='app'></div></body></html>")
    saved = service.save(URL)

    service.drain()

    assert service.get_item(saved.item.id).failure_reason == "no readable content"


def test_a_wall_from_the_server_loses_to_real_client_html(service, fetcher, summariser):
    fetcher.page(URL, JS_SHELL)
    saved = service.save(URL, html=ARTICLE)

    service.drain()

    assert service.get_item(saved.item.id).status == "summarised"


@pytest.mark.parametrize(
    "failure",
    [
        ProviderFailure("rate_limit", "Claude AI usage limit reached", retryable=False),
        ProviderFailure("auth", "Error: not logged in. Run /login", retryable=False),
    ],
)
def test_systemic_failure_stops_the_run_and_counts_nothing(
    service, fetcher, summariser, clock, failure
):
    for n in range(3):
        fetcher.page(f"{URL}/{n}", ARTICLE)
        service.save(f"{URL}/{n}")
    summariser.script(failure)

    for _ in range(5):
        report = service.drain()
        clock.advance(minutes=10)

    assert report.stopped.startswith(failure.failure_class)
    assert len(summariser.requests) == 5  # one call per run, then stop
    statuses = service.conn.execute("SELECT status FROM item").fetchall()
    assert {row["status"] for row in statuses} == {"pending"}

    summariser.script(summary_json())
    report = service.drain()
    assert report.summarised == 3


def test_circuit_breaker_stops_after_consecutive_transient_failures(
    service, fetcher, summariser
):
    for n in range(7):
        fetcher.page(f"{URL}/{n}", ARTICLE)
        service.save(f"{URL}/{n}")
    summariser.script(ProviderFailure("transient", "segfault", retryable=True))

    report = service.drain()

    assert report.retry == 5
    assert report.stopped.startswith("circuit breaker")


def test_resaving_a_failed_item_requeues_it(service, fetcher, summariser, clock):
    fetcher.page(URL, JS_SHELL)
    first = service.save(URL, note="the original note")
    service.drain()
    assert service.get_item(first.item.id).status == "failed"
    clock.advance(days=2)

    again = service.save(URL, html=ARTICLE, note="new note")

    assert again.outcome == "requeued"
    assert again.message == "Re-queued; note not added"
    item = service.get_item(first.item.id)
    assert item.status == "pending"
    assert item.failure_reason is None
    assert item.note == "the original note"
    assert item.saved_at == "2026-09-30T12:00:00Z"

    service.drain()
    assert service.get_item(first.item.id).status == "summarised"
    assert "Conflict-free" in summariser.requests[-1].user_prompt


def test_requeue_resets_attempts(service, fetcher, summariser, clock):
    fetcher.script(URL, FetchError("timeout", "timed out"))
    saved = service.save(URL)
    _drain_attempts(service, clock, 3)
    assert service.get_item(saved.item.id).status == "failed"

    service.save(URL)
    service.drain()

    item = service.get_item(saved.item.id)
    assert item.status == "pending"  # one fresh attempt used, two left


def test_unreadable_reply_is_permanent(service, fetcher, summariser):
    fetcher.page(URL, ARTICLE)
    summariser.script(json.dumps({"unreadable": "captcha"}))
    saved = service.save(URL)

    report = service.drain()

    assert report.failed == 1
    assert service.get_item(saved.item.id).failure_reason == "unreadable: captcha"
