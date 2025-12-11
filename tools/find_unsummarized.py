#!/usr/bin/env python3
"""
Script to find bookmarks with 'unsummarized' tag.
Displays URL, title, description, and other metadata for bookmarks needing LLM summaries.
"""

import argparse
import json

from javascript_data_files import read_js

from bookmarks.data.datafile import get_data_source


def main():
    parser = argparse.ArgumentParser(
        description="Find bookmarks with 'unsummarized' tag (bookmarks needing LLM descriptions).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show next 10 unsummarized bookmarks
  python find_unsummarized.py

  # Show next 5 unsummarized bookmarks
  python find_unsummarized.py --count 5

  # Show next 20 unsummarized bookmarks with detailed info
  python find_unsummarized.py --count 20 --detailed

  # Export unsummarized entries as JSON (for use with update_bookmarks.py)
  python find_unsummarized.py --count 10 --json-output unsummarized.json
        """,
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of unsummarized entries to display (default: 10)",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed information including description and tags",
    )
    parser.add_argument("--json-output", type=str, help="Output results to a JSON file")
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="Skip the first N unsummarized entries (default: 0)",
    )

    args = parser.parse_args()

    data_source = get_data_source()
    bookmarks = read_js(data_source, varname="bookmarks")

    # Find all unsummarized bookmarks with their indices
    unsummarized_entries = []
    for i, bookmark in enumerate(bookmarks):
        if "unsummarized" in bookmark.get("tags", []):
            unsummarized_entries.append({"index": i, "bookmark": bookmark})

    total_unsummarized = len(unsummarized_entries)
    print(f"Total unsummarized entries: {total_unsummarized}")

    if total_unsummarized == 0:
        print("No unsummarized entries found!")
        return

    # Apply skip and count
    start_idx = args.skip
    end_idx = min(start_idx + args.count, total_unsummarized)
    selected_entries = unsummarized_entries[start_idx:end_idx]

    if args.skip > 0:
        print(f"Skipping first {args.skip} entries")
    print(f"Showing entries {start_idx + 1} to {end_idx} of {total_unsummarized}\n")

    # Display entries
    for i, entry in enumerate(selected_entries, start=1):
        idx = entry["index"]
        bookmark = entry["bookmark"]

        print(f"{i}. [Index: {idx}] {bookmark.get('title', 'No title')}")
        print(f"   URL: {bookmark.get('url', 'No URL')}")

        if args.detailed:
            print(f"   Date Added: {bookmark.get('dateAdded', 'Unknown')}")

            desc = bookmark.get("description", "No description")
            if desc:
                # Truncate long descriptions
                if len(desc) > 200 and not args.json_output:
                    desc = desc[:200] + "..."
                print(f"   Description: {desc}")

            tags = bookmark.get("tags", [])
            print(f"   Tags: {', '.join(tags)}")

            if "summarized" in bookmark:
                print(f"   Summarized: {bookmark['summarized']}")

        print()

    # Export to JSON if requested
    if args.json_output:
        output_data = []
        for entry in selected_entries:
            output_data.append(
                {
                    "index": entry["index"],
                    "url": entry["bookmark"].get("url"),
                    "title": entry["bookmark"].get("title"),
                    "description": entry["bookmark"].get("description", ""),
                    "tags": entry["bookmark"].get("tags", []),
                    "dateAdded": entry["bookmark"].get("dateAdded"),
                    "summarized": entry["bookmark"].get("summarized"),
                }
            )

        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\nExported {len(output_data)} entries to {args.json_output}")


if __name__ == "__main__":
    main()
