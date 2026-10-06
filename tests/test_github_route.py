"""GitHub repo URLs are summarised from the README returned by the API."""

from dataclasses import replace

import pytest

from bookmarks.ingest.fetch import HttpResponse
from bookmarks.ingest.github import repo_of
from tests.factories import fixture_text, item_at, submission_at

REPO_URL = "https://github.com/automerge/automerge"
API = "https://api.github.com/repos/automerge/automerge"
ARTICLE = fixture_text("article.html")


def _script_repo(fetcher, readme_status=200):
    fetcher.script(API, HttpResponse(200, fixture_text("github_repo.json")))
    readme = "github_readme.json" if readme_status == 200 else "github_not_found.json"
    fetcher.script(f"{API}/readme", HttpResponse(readme_status, fixture_text(readme)))


def test_repo_url_is_summarised_from_the_api_readme(service, fetcher, summariser):
    _script_repo(fetcher)
    service.save(REPO_URL)

    service.drain()

    prompt = summariser.requests[0].user_prompt
    assert "Automerge is a library of data structures" in prompt
    assert "Page title: automerge/automerge" in prompt
    assert "Page description: A JSON-like data structure" in prompt
    assert item_at(service, REPO_URL) is not None
    assert all(url.startswith("https://api.github.com/") for url, _ in fetcher.requests)
    assert fetcher.requests[0][1]["Accept"] == "application/vnd.github+json"


def test_readme_wins_even_when_client_html_is_longer(service, fetcher, summariser):
    _script_repo(fetcher)
    service.save(REPO_URL, html=ARTICLE * 5)

    service.drain()

    prompt = summariser.requests[0].user_prompt
    assert "Automerge is a library of data structures" in prompt
    assert "Cloud apps like Google Docs" not in prompt


def test_missing_repo_fails_permanently(service, fetcher, summariser):
    fetcher.script(API, HttpResponse(404, fixture_text("github_not_found.json")))
    service.save(REPO_URL)

    service.drain()

    submission = submission_at(service, REPO_URL)
    assert submission.status == "failed"
    assert submission.failure_reason == "retrieving: GitHub repository not found"
    assert summariser.requests == []


def test_github_api_5xx_is_transient(service, fetcher):
    fetcher.script(API, HttpResponse(502, "Bad Gateway"))
    service.save(REPO_URL)

    report = service.drain()

    assert report.retry == 1
    assert submission_at(service, REPO_URL).status == "pending"


def test_repo_without_readme_falls_back_to_the_generic_route(
    service, fetcher, summariser
):
    _script_repo(fetcher, readme_status=404)
    service.save(REPO_URL, html=ARTICLE)

    service.drain()

    assert "Cloud apps like Google Docs" in summariser.requests[0].user_prompt


def test_token_is_sent_when_configured(make_service, settings, fetcher):
    service = make_service(settings=replace(settings, github_token="tkn"))
    _script_repo(fetcher)
    service.save(REPO_URL)

    service.drain()

    assert fetcher.requests[0][1]["Authorization"] == "Bearer tkn"


def test_non_repo_github_url_uses_the_generic_route(service, fetcher, summariser):
    issue = "https://github.com/automerge/automerge/issues/42"
    fetcher.page(issue, ARTICLE)
    service.save(issue)

    service.drain()

    assert [url for url, _ in fetcher.requests] == [issue]
    assert "Cloud apps like Google Docs" in summariser.requests[0].user_prompt


@pytest.mark.parametrize(
    "url,repo",
    [
        ("https://github.com/automerge/automerge", ("automerge", "automerge")),
        ("https://www.github.com/a/b/", ("a", "b")),
        ("https://github.com/a/b.git", ("a", "b")),
        ("https://github.com/a/b/tree/main/src", None),
        ("https://github.com/automerge", None),
        ("https://github.com/features/copilot", None),
        ("https://github.com/topics/crdt", None),
        ("https://gitlab.com/a/b", None),
        ("https://gist.github.com/a/b", None),
    ],
)
def test_repo_url_rule(url, repo):
    found = repo_of(url)
    assert ((found.owner, found.name) if found else None) == repo
