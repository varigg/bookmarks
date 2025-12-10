"""Data access layer."""

from .datafile import get_data, write_data
from .repository import BookmarkRepository

__all__ = [
    "BookmarkRepository",
    "get_data",
    "write_data",
]
