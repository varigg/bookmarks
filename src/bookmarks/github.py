"""GitHub route: a repo URL is summarised from its README via the REST API."""

import base64
import binascii
import json
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from bookmarks.fetch import Fetcher, FetchError, HttpResponse

API = "https://api.github.com"

# First path segments that are GitHub's own pages, not owners.
_RESERVED = frozenset(
    {
        "about", "apps", "codespaces", "collections", "contact", "customer-stories",
        "enterprise", "events", "explore", "features", "issues", "join", "login",
        "marketplace", "new", "notifications", "orgs", "pricing", "pulls",
        "readme", "search", "security", "settings", "site", "sponsors", "team",
        "topics", "trending", "users",
    }
)  # fmt: skip
_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class Repo:
    owner: str
    name: str


def repo_of(url: str) -> Repo | None:
    """The repo a URL points at, for exactly github.com/<owner>/<repo>[/]."""
    parts = urlsplit(url)
    if (parts.hostname or "").lower() not in ("github.com", "www.github.com"):
        return None
    segments = [s for s in parts.path.split("/") if s]
    if len(segments) != 2:
        return None
    owner, name = segments[0], segments[1].removesuffix(".git")
    if owner.lower() in _RESERVED or not (_NAME.match(owner) and _NAME.match(name)):
        return None
    return Repo(owner=owner, name=name)


class GitHubFailure(Exception):
    def __init__(self, reason: str, *, transient: bool) -> None:
        super().__init__(reason)
        self.reason = reason
        self.transient = transient


@dataclass(frozen=True)
class Readme:
    full_name: str
    description: str | None
    text: str | None  # None when the repo has no README


def _get(fetcher: Fetcher, url: str, token: str | None) -> HttpResponse:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        return fetcher.get(url, headers=headers)
    except FetchError as exc:
        raise GitHubFailure(str(exc), transient=True) from None


def _raise_for(response: HttpResponse, what: str) -> None:
    if response.status in (404, 410, 451):
        raise GitHubFailure(f"GitHub {what} not found", transient=False)
    if response.status in (403, 429):
        raise GitHubFailure("GitHub API rate limit", transient=True)
    if response.status >= 500:
        raise GitHubFailure(
            f"GitHub API error (HTTP {response.status})", transient=True
        )
    raise GitHubFailure(f"GitHub API HTTP {response.status}", transient=False)


def _json(response: HttpResponse) -> dict:
    try:
        data = json.loads(response.text)
    except json.JSONDecodeError:
        raise GitHubFailure("GitHub API returned non-JSON", transient=True) from None
    if not isinstance(data, dict):
        raise GitHubFailure("GitHub API returned non-object JSON", transient=True)
    return data


def fetch_readme(fetcher: Fetcher, repo: Repo, token: str | None = None) -> Readme:
    base = f"{API}/repos/{repo.owner}/{repo.name}"
    meta = _get(fetcher, base, token)
    if meta.status != 200:
        _raise_for(meta, "repository")
    info = _json(meta)
    full_name = str(info.get("full_name") or f"{repo.owner}/{repo.name}")
    description = (info.get("description") or "").strip() or None

    response = _get(fetcher, f"{base}/readme", token)
    if response.status == 404:
        return Readme(full_name=full_name, description=description, text=None)
    if response.status != 200:
        _raise_for(response, "README")
    readme = _json(response)
    try:
        text = base64.b64decode(readme.get("content") or "").decode("utf-8", "replace")
    except (binascii.Error, ValueError):
        raise GitHubFailure("GitHub README not decodable", transient=True) from None
    return Readme(full_name=full_name, description=description, text=text.strip())
