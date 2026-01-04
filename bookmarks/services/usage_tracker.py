"""
Usage tracker for LLM API calls.
Tracks requests, tokens, and estimated cost by month and provider.
"""

import json
import os
from datetime import datetime
from typing import Any

USAGE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "usage_stats.json")


class UsageTracker:
    """Tracks API usage statistics locally, separated by provider."""

    def __init__(self, provider: str = "unknown", filepath: str = USAGE_FILE):
        """
        Initialize the usage tracker.

        Args:
            provider: LLM provider name (e.g., "perplexity", "openai", "anthropic")
            filepath: Path to the JSON file storing usage stats.
        """
        self.provider = provider
        self.filepath = filepath
        self.stats = self._load_stats()

    def _load_stats(self) -> dict[str, dict[str, Any]]:
        """Load stats from file or return empty dict."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                return {}
        return {}

    def _save_stats(self):
        """Save stats to file."""
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.stats, f, indent=2)
        except OSError as e:
            print(f"Warning: Could not save usage stats: {e}")

    def track_request(self, tokens: int = 0, cost: float = 0.0):
        """
        Track a single API request for the current provider.

        Args:
            tokens: Number of tokens used.
            cost: Estimated cost in USD.
        """
        # Reload to ensure we don't overwrite other providers' updates
        self.stats = self._load_stats()

        month = datetime.now().strftime("%Y-%m")

        # Initialize month if needed
        if month not in self.stats:
            self.stats[month] = {}

        # Initialize provider stats if needed
        if self.provider not in self.stats[month]:
            self.stats[month][self.provider] = {
                "requests": 0,
                "tokens": 0,
                "cost": 0.0,
            }

        # Update stats for this provider
        self.stats[month][self.provider]["requests"] += 1
        self.stats[month][self.provider]["tokens"] += tokens
        self.stats[month][self.provider]["cost"] += cost

        self._save_stats()

    def get_stats(self, month: str | None = None, provider: str | None = None) -> dict[str, Any]:
        """
        Get usage statistics.

        Args:
            month: Specific month (YYYY-MM) to get stats for.
                   If None, returns all months.
            provider: Specific provider to get stats for.
                     If None, uses tracker's provider.

        Returns:
            Dict containing usage stats.
        """
        # Reload to get latest data from other instances
        self.stats = self._load_stats()

        target_provider = provider or self.provider

        if month:
            month_stats = self.stats.get(month, {})
            return month_stats.get(target_provider, {"requests": 0, "tokens": 0, "cost": 0.0})
        return self.stats

    def get_current_month_stats(self, provider: str | None = None) -> dict[str, Any]:
        """
        Get stats for the current month and provider.

        Args:
            provider: Specific provider to get stats for.
                     If None, uses tracker's provider.

        Returns:
            Dict with usage stats for the provider.
        """
        month = datetime.now().strftime("%Y-%m")
        return self.get_stats(month, provider)

    def get_all_providers_stats(self, month: str | None = None) -> dict[str, Any]:
        """
        Get stats for all providers.

        Args:
            month: Specific month (YYYY-MM) to get stats for.
                   If None, uses current month.

        Returns:
            Dict mapping provider names to their stats.
        """
        # Reload to ensure we have latest data
        self.stats = self._load_stats()

        target_month = month or datetime.now().strftime("%Y-%m")
        return self.stats.get(target_month, {})
