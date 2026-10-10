"""Smoke tests for the capture endpoint: validation and pass-through."""

import pytest
from fastapi.testclient import TestClient

from bookmarks.web.app import create_app
from tests.factories import is_recent, submission_at


@pytest.fixture
def client(open_service):
    return TestClient(create_app(open_service))


def test_post_url_answers_url_status_and_saved_time(client):
    response = client.post(
        "/api/items",
        json={"url": "https://example.com/a?utm_source=x", "html": "<p>hi</p>"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "Saved"
    assert body["item"] == {
        "url": "https://example.com/a",
        "status": "pending",
        "saved_at": body["item"]["saved_at"],
    }
    assert is_recent(body["item"]["saved_at"])


def test_duplicate_post_reports_already_saved(client):
    client.post("/api/items", json={"url": "https://example.com/a"})

    response = client.post(
        "/api/items", json={"url": "https://example.com/a", "note": "why"}
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "already_saved"
    assert response.json()["note_added"] is False


@pytest.mark.parametrize("payload", [{}, {"url": 5}, {"url": "ftp://x.org/"}])
def test_invalid_payloads_are_rejected(client, payload):
    assert client.post("/api/items", json=payload).status_code == 422


def test_empty_strings_are_absent_fields(client, service):
    """The iOS Shortcut cannot omit a JSON key, so it sends "" for a field it
    has no value for (ios-shortcut/README.md depends on this)."""
    response = client.post(
        "/api/items",
        json={"url": "https://example.com/p", "html": "", "title": "", "note": ""},
    )

    assert response.status_code == 201
    assert response.json()["note_added"] is False
    submission = submission_at(service, "https://example.com/p")
    assert (submission.note, submission.status) == (None, "pending")


def test_a_rejected_url_replies_with_detail_and_no_message(client):
    """The Shortcut shows `message` when there is one and `detail` otherwise."""
    response = client.post("/api/items", json={"url": "ftp://example.com/p"})

    assert response.status_code == 422
    assert "message" not in response.json()
    assert "not an http(s) URL" in response.json()["detail"]
