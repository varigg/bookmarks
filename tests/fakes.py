"""Scripted fakes for the core's external edges."""

import json
from datetime import UTC, datetime, timedelta

from bookmarks.fetch import FetchError, HttpResponse
from bookmarks.llm.provider import LLMRequest, LLMResult


class FakeClock:
    def __init__(self, start: datetime | None = None) -> None:
        self.current = start or datetime(2026, 9, 30, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> None:
        self.current += timedelta(**delta)


class FakeFetcher:
    """Responses scripted per URL; an unscripted URL cannot be reached."""

    def __init__(self) -> None:
        self.routes: dict[str, list] = {}
        self.requests: list[tuple[str, dict]] = []

    def script(self, url: str, *responses) -> None:
        """Each fetch of `url` takes the next response; the last one repeats."""
        self.routes[url] = list(responses)

    def page(self, url: str, html: str, status: int = 200) -> None:
        self.script(url, HttpResponse(status=status, text=html))

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> HttpResponse:
        self.requests.append((url, headers or {}))
        responses = self.routes.get(url)
        if not responses:
            raise FetchError("network", f"unscripted URL {url}")
        response = responses.pop(0) if len(responses) > 1 else responses[0]
        if isinstance(response, Exception):
            raise response
        return response


def summary_json(
    title: str = "A Title",
    type: str = "article",
    summary: str = "A lede that stands alone. More detail follows here.",
    entities: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "title": title,
            "type": type,
            "summary": summary,
            "entities": entities if entities is not None else ["CRDT"],
        }
    )


class FakeSummariser:
    """Replies scripted in order; the last one repeats. Records every request."""

    name = "claude-cli"

    def __init__(self, model: str = "claude-sonnet-5-5") -> None:
        self.model = model
        self.replies: list = [summary_json()]
        self.requests: list[LLMRequest] = []

    def script(self, *replies) -> None:
        self.replies = list(replies)

    def submit(self, request: LLMRequest) -> LLMResult:
        self.requests.append(request)
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, Exception):
            raise reply
        return LLMResult(text=reply, model=self.model, raw=reply)
