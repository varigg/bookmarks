#!/usr/bin/env python3
"""
Test script for UsageTracker.
"""

import os
import unittest
from datetime import datetime
from bookmarks.services import UsageTracker

TEST_USAGE_FILE = "test_usage_stats.json"


class TestUsageTracker(unittest.TestCase):
    def setUp(self):
        # Clean up test file
        if os.path.exists(TEST_USAGE_FILE):
            os.remove(TEST_USAGE_FILE)

    def tearDown(self):
        # Clean up test file
        if os.path.exists(TEST_USAGE_FILE):
            os.remove(TEST_USAGE_FILE)

    def test_track_request(self):
        tracker = UsageTracker(TEST_USAGE_FILE)
        tracker.track_request(tokens=100, cost=0.005)

        month = datetime.now().strftime("%Y-%m")
        stats = tracker.get_stats(month)

        self.assertEqual(stats["requests"], 1)
        self.assertEqual(stats["tokens"], 100)
        self.assertEqual(stats["cost"], 0.005)

        # Track another request
        tracker.track_request(tokens=50, cost=0.002)
        stats = tracker.get_stats(month)

        self.assertEqual(stats["requests"], 2)
        self.assertEqual(stats["tokens"], 150)
        self.assertAlmostEqual(stats["cost"], 0.007)

    def test_persistence(self):
        tracker = UsageTracker(TEST_USAGE_FILE)
        tracker.track_request(tokens=100, cost=0.005)

        # Create new tracker instance
        tracker2 = UsageTracker(TEST_USAGE_FILE)
        month = datetime.now().strftime("%Y-%m")
        stats = tracker2.get_stats(month)

        self.assertEqual(stats["requests"], 1)
        self.assertEqual(stats["tokens"], 100)


if __name__ == "__main__":
    unittest.main()
