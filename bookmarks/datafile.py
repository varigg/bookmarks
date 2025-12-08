#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data file I/O operations for bookmarks.

This module handles reading and writing bookmark data to/from JavaScript files.
"""

from typing import Any

from dynaconf import settings
from javascript_data_files import read_js, write_js


def get_data_source() -> str:
    """
    Get the configured data source path.
    
    Returns:
        Path to the data source file from settings.
    """
    return settings.DATA_SOURCE


def get_data() -> list[dict[str, Any]]:
    """
    Read bookmark data from the configured data source.
    
    Returns:
        List of bookmark dictionaries.
    """
    return read_js(get_data_source(), varname="bookmarks")


def write_data(data: list[dict[str, Any]] | Any) -> None:
    """
    Write bookmark data to the configured data source.
    
    Args:
        data: Iterable of bookmark dictionaries to write.
    """
    write_js(get_data_source(), value=list(data), varname="bookmarks")
