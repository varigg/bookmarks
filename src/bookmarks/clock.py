"""Stored timestamps."""

from datetime import UTC, datetime


def now_iso() -> str:
    """Now in stored timestamp form: UTC, second precision, trailing Z."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
