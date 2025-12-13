"""
Convert a tag across all bookmarks to a new tag name.
"""

import argparse

from bookmarks.model import get_bookmarks, save_bookmark

bookmarks = get_bookmarks()
counter = 0


def change_tag(id, bookmark, old_tag, new_tag, dry_run):
    global counter
    if old_tag in bookmark["tags"]:
        bookmark["tags"].remove(old_tag)
        counter += 1
        if new_tag not in bookmark["tags"]:
            bookmark["tags"].append(new_tag)
        if not dry_run:
            save_bookmark(id, bookmark)


def main():
    parser = argparse.ArgumentParser(
        description="Convert a tag across all bookmarks to a new tag name."
    )
    parser.add_argument("old_tag", type=str, help="The old tag name to convert.")
    parser.add_argument("new_tag", type=str, help="The new tag name to convert to.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually change any tags, just print what would happen.",
    )
    args = parser.parse_args()
    for id in bookmarks:
        change_tag(id, bookmarks[id], args.old_tag, args.new_tag, args.dry_run)
    print(f"changed {counter} tags")


if __name__ == "__main__":
    main()
