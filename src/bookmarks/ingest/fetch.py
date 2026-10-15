"""What the retrieving stage asks of the network.

The core sees `HttpResponse` or `FetchError`, never httpx.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class HttpResponse:
    status: int
    text: str


class FetchError(Exception):
    """No HTTP response at all: timeout, DNS, connection refused, TLS."""


class Unretrievable(Exception):
    """No source text; `transient` says whether a later drain may succeed."""

    def __init__(self, reason: str, *, transient: bool) -> None:
        super().__init__(reason)
        self.reason = reason
        self.transient = transient


class Fetcher(Protocol):
    def get(
        self, url: str, *, headers: dict[str, str] | None = None
    ) -> HttpResponse: ...
