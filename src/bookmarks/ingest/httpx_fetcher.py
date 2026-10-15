"""HTTP fetch edge: the httpx adapter for `Fetcher`."""

import httpx

from bookmarks.ingest.fetch import FetchError, HttpResponse

_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"


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
            raise FetchError(f"timed out fetching {url}: {exc}") from None
        except httpx.HTTPError as exc:
            raise FetchError(f"could not fetch {url}: {exc}") from None
        return HttpResponse(status=response.status_code, text=response.text)
