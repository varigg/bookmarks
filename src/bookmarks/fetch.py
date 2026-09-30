"""HTTP fetch edge. The core sees `HttpResponse` or `FetchError`, never httpx."""

from dataclasses import dataclass, field
from typing import Protocol

import httpx

_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"


@dataclass(frozen=True)
class HttpResponse:
    status: int
    text: str
    headers: dict[str, str] = field(default_factory=dict)


class FetchError(Exception):
    """No HTTP response at all: timeout, DNS, connection refused, TLS."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


class Fetcher(Protocol):
    def get(
        self, url: str, *, headers: dict[str, str] | None = None
    ) -> HttpResponse: ...


class HttpxFetcher:
    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> HttpResponse:
        request_headers = {"User-Agent": _USER_AGENT, **(headers or {})}
        try:
            response = httpx.get(
                url,
                headers=request_headers,
                timeout=self.timeout,
                follow_redirects=True,
            )
        except httpx.TimeoutException as exc:
            raise FetchError("timeout", f"timed out fetching {url}: {exc}") from None
        except httpx.HTTPError as exc:
            raise FetchError("network", f"could not fetch {url}: {exc}") from None
        return HttpResponse(
            status=response.status_code,
            text=response.text,
            headers=dict(response.headers),
        )
