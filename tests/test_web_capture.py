"""Smoke tests for the capture endpoint: validation and pass-through."""

import pytest
from fastapi.testclient import TestClient

from bookmarks.web.app import create_app


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
        "saved_at": "2026-09-30T12:00:00Z",
    }


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
