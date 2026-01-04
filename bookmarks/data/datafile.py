#!/usr/bin/env python3
"""
Data file I/O operations for bookmarks.

This module handles reading and writing bookmark data to/from JavaScript files.
"""

from typing import Any

from javascript_data_files import read_js, write_js

from bookmarks import config


def get_data_source() -> str:
    """
    Get the configured data source path.

    Returns:
        Path to the data source file from settings.
    """
    return config.DATA_SOURCE


def get_data() -> list[dict[str, Any]]:
    """
    Read bookmark data from the configured data source.

    If the data file doesn't exist, creates an empty one automatically.

    Returns:
        List of bookmark dictionaries.
    """
    from pathlib import Path

    data_source = get_data_source()
    data_path = Path(data_source)

    # Auto-create empty bookmarks file if it doesn't exist
    if not data_path.exists():
        # Ensure parent directory exists
        data_path.parent.mkdir(parents=True, exist_ok=True)

        # Create empty bookmarks file
        write_js(data_source, value=[], varname="bookmarks")
        return []

    return read_js(data_source, varname="bookmarks")


def write_data(data: list[dict[str, Any]] | Any) -> None:
    """
    Write bookmark data to the configured data source.

    Args:
        data: Iterable of bookmark dictionaries to write.
    """
    write_js(get_data_source(), value=list(data), varname="bookmarks")
