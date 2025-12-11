#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Usage tracker for Perplexity API calls.
Tracks requests, tokens, and estimated cost by month.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

USAGE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "usage_stats.json"
)


class UsageTracker:
    """Tracks API usage statistics locally."""

    def __init__(self, filepath: str = USAGE_FILE):
        """
        Initialize the usage tracker.

        Args:
            filepath: Path to the JSON file storing usage stats.
        """
        self.filepath = filepath
        self.stats = self._load_stats()

    def _load_stats(self) -> Dict[str, Dict[str, Any]]:
        """Load stats from file or return empty dict."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_stats(self):
        """Save stats to file."""
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.stats, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save usage stats: {e}")

    def track_request(self, tokens: int = 0, cost: float = 0.0):
        """
        Track a single API request.

        Args:
            tokens: Number of tokens used.
            cost: Estimated cost in USD.
        """
        month = datetime.now().strftime("%Y-%m")

        if month not in self.stats:
            self.stats[month] = {"requests": 0, "tokens": 0, "cost": 0.0}

        self.stats[month]["requests"] += 1
        self.stats[month]["tokens"] += tokens
        self.stats[month]["cost"] += cost

        self._save_stats()

    def get_stats(self, month: Optional[str] = None) -> Dict[str, Any]:
        """
        Get usage statistics.

        Args:
            month: Specific month (YYYY-MM) to get stats for.
                   If None, returns all stats.

        Returns:
            Dict containing usage stats.
        """
        if month:
            return self.stats.get(month, {"requests": 0, "tokens": 0, "cost": 0.0})
        return self.stats

    def get_current_month_stats(self) -> Dict[str, Any]:
        """Get stats for the current month."""
        month = datetime.now().strftime("%Y-%m")
        return self.get_stats(month)
