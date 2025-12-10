"""
Retrieve all tags from bookmarks.
"""

import argparse
from bookmarks.model import get_bookmarks


def main():
    parser = argparse.ArgumentParser(description="Retrieve all tags from bookmarks.")
    args = parser.parse_args()
    bookmarks = get_bookmarks()
    tags = set()
    for id in bookmarks:
        tags.update(bookmarks[id]["tags"])
    print(", ".join(tags))


if __name__ == "__main__":
    main()
