#!/usr/bin/env python3
"""
Convert dateAdded timestamps from Unix epoch format to ISO 8601 format.
This script reads bookmarks.js, converts all Unix timestamps to ISO format,
and writes the updated data back.
"""

from datetime import datetime, timezone

from bookmarks.model import get_bookmarks, save_bookmark


def convert_unix_to_iso(unix_timestamp):
    """
    Convert Unix timestamp (seconds since epoch) to ISO 8601 format.
    Matches the format used by 'summarized' field: YYYY-MM-DDTHH:MM:SS.mmmmmm (no timezone suffix)

    Args:
        unix_timestamp: String or int representing seconds since Unix epoch

    Returns:
        ISO 8601 formatted timestamp string without timezone
    """
    try:
        # Handle both string and int input
        timestamp = int(unix_timestamp)
        # Convert to datetime object in UTC
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        # Return ISO format string without timezone (to match 'summarized' format)
        # Replace tzinfo to get naive datetime, then format with microseconds
        return dt.replace(tzinfo=None).isoformat()
    except (ValueError, TypeError):
        # If already in ISO format or invalid, return as-is
        return unix_timestamp


def is_unix_timestamp(value):
    """
    Check if a value looks like a Unix timestamp (numeric string or int).

    Args:
        value: The value to check

    Returns:
        True if it appears to be a Unix timestamp, False otherwise
    """
    if isinstance(value, int):
        return True
    if isinstance(value, str):
        # Unix timestamps are typically 10 digits (seconds) or 13 digits (milliseconds)
        # and don't contain any non-numeric characters
        return value.isdigit() and len(value) in [10, 13]
    return False


def convert_all_timestamps():
    """
    Convert all dateAdded fields from Unix timestamps to ISO format.
    """
    bookmarks = get_bookmarks()
    converted_count = 0
    skipped_count = 0

    print("Starting timestamp conversion...")
    print(f"Total bookmarks: {len(bookmarks)}\n")

    for id, bookmark in bookmarks.items():
        date_added = bookmark.get("dateAdded")

        if not date_added:
            print(f"Bookmark {id}: No dateAdded field, skipping")
            skipped_count += 1
            continue

        # Check if it's a Unix timestamp
        if is_unix_timestamp(date_added):
            old_value = date_added
            new_value = convert_unix_to_iso(date_added)
            bookmark["dateAdded"] = new_value
            save_bookmark(id, bookmark)
            converted_count += 1
            print(f"Bookmark {id}: {old_value} -> {new_value}")
        else:
            # Already in ISO format or unknown format
            skipped_count += 1
            if converted_count + skipped_count <= 5:  # Show first few
                print(f"Bookmark {id}: Already ISO format: {date_added}")

    print(f"\n{'=' * 60}")
    print("Conversion complete!")
    print(f"Converted: {converted_count} bookmarks")
    print(f"Skipped: {skipped_count} bookmarks (already in ISO format or no date)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    # Confirm before running
    print("This script will convert all Unix timestamps to ISO 8601 format.")
    print("The changes will be saved to bookmarks.js")
    response = input("\nContinue? (yes/no): ")

    if response.lower() in ["yes", "y"]:
        convert_all_timestamps()
    else:
        print("Conversion cancelled.")
