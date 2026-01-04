from datetime import datetime

from bookmarks.services.usage_tracker import UsageTracker


def test_usage_tracker_initialization(tmp_path):
    usage_file = tmp_path / "usage.json"
    tracker = UsageTracker(provider="test-provider", filepath=str(usage_file))
    assert tracker.provider == "test-provider"
    assert tracker.filepath == str(usage_file)
    assert tracker.stats == {}


def test_track_request(tmp_path):
    usage_file = tmp_path / "usage.json"
    tracker = UsageTracker(provider="test-provider", filepath=str(usage_file))

    tracker.track_request(tokens=100, cost=0.01)

    month = datetime.now().strftime("%Y-%m")
    stats = tracker.get_stats(month=month)

    assert stats["requests"] == 1
    assert stats["tokens"] == 100
    assert stats["cost"] == 0.01


def test_usage_tracker_persistence(tmp_path):
    usage_file = tmp_path / "usage.json"
    tracker1 = UsageTracker(provider="test-provider", filepath=str(usage_file))
    tracker1.track_request(tokens=50, cost=0.005)

    # New instance should load from file
    tracker2 = UsageTracker(provider="test-provider", filepath=str(usage_file))
    month = datetime.now().strftime("%Y-%m")
    stats = tracker2.get_stats(month=month)

    assert stats["requests"] == 1
    assert stats["tokens"] == 50


def test_get_all_providers_stats(tmp_path):
    usage_file = tmp_path / "usage.json"
    tracker_p1 = UsageTracker(provider="p1", filepath=str(usage_file))
    tracker_p2 = UsageTracker(provider="p2", filepath=str(usage_file))

    tracker_p1.track_request(tokens=10, cost=0.1)
    tracker_p2.track_request(tokens=20, cost=0.2)

    all_stats = tracker_p1.get_all_providers_stats()
    assert "p1" in all_stats
    assert "p2" in all_stats
    assert all_stats["p1"]["tokens"] == 10
    assert all_stats["p2"]["tokens"] == 20
