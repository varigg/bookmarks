"""Clock edge: the core never reads the wall clock directly."""

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def to_iso(moment: datetime) -> str:
    """Stored timestamp form: UTC, second precision, trailing Z."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
