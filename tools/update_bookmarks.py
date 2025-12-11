import argparse
import datetime
import json

from javascript_data_files import read_js, write_js

from bookmarks.data.datafile import get_data_source


def main():
    parser = argparse.ArgumentParser(description="Update bookmarks from a JSON file.")
    parser.add_argument(
        "--start-index",
        type=int,
        help="(Optional) The starting index in the bookmarks array to update. If not provided, uses index field from each update.",
    )
    parser.add_argument(
        "--json-file",
        type=str,
        required=True,
        help="A file containing a JSON string with a list of update objects.",
    )
    args = parser.parse_args()

    data_source = get_data_source()
    bookmarks = read_js(data_source, varname="bookmarks")

    with open(args.json_file, "r") as f:
        updates = json.load(f)

    for i, update_data in enumerate(updates):
        # Use index from update_data if available, otherwise use start-index + i
        if "index" in update_data:
            index = update_data["index"]
        elif args.start_index is not None:
            index = args.start_index + i
        else:
            raise ValueError(
                f"Update {i} has no 'index' field and no --start-index was provided"
            )

        if index < len(bookmarks):
            bookmarks[index]["description"] = update_data["description"]
            bookmarks[index]["title"] = update_data["title"]

            # Ensure tags list exists
            if "tags" not in bookmarks[index]:
                bookmarks[index]["tags"] = []

            # Remove "unsummarized" tag if it exists
            if "unsummarized" in bookmarks[index]["tags"]:
                bookmarks[index]["tags"].remove("unsummarized")

            # Add new tags, avoiding duplicates
            for tag in update_data["tags"]:
                if tag not in bookmarks[index]["tags"]:
                    bookmarks[index]["tags"].append(tag)

            bookmarks[index]["summarized"] = datetime.datetime.now().isoformat()
        else:
            print(
                f"Warning: Index {index} is out of range (bookmarks has {len(bookmarks)} entries)"
            )

    write_js(data_source, value=list(bookmarks), varname="bookmarks")


if __name__ == "__main__":
    main()
