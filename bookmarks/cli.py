"""
Fetch and convert a webpage to readable content.

Usage:
    fetch_web_content https://example.com
    fetch_web_content https://example.com --format html
    fetch_web_content https://example.com --max-chars 16000
"""

import argparse
import sys

from bookmarks.services.content_extractor import HTMLExtractor, MarkdownExtractor


def main():
    parser = argparse.ArgumentParser(
        description="Fetch and convert a webpage to readable content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("url", help="URL to fetch and convert")
    parser.add_argument(
        "--format",
        choices=["html", "markdown"],
        default="markdown",
        help="Extraction format: 'markdown' (MarkItDown) or 'html' (BeautifulSoup plain text). Default: markdown",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=8000,
        help="Maximum characters of body content to output (default: 8000)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="HTTP request timeout in seconds (default: 10)",
    )

    args = parser.parse_args()

    if args.format == "markdown":
        extractor = MarkdownExtractor(max_chars=args.max_chars)
        result = extractor.extract(args.url, timeout=args.timeout)
        print(f"Title: {result['title']}")
        print(f"URL:   {result['url']}")
        print()
        print(result["markdown"])
    else:
        extractor = HTMLExtractor()
        result = extractor.extract(args.url, timeout=args.timeout)
        text = result["text"]
        if len(text) > args.max_chars:
            text = text[: args.max_chars] + "..."
        print(f"Title:            {result['title']}")
        print(f"Meta description: {result['meta_description']}")
        print()
        print(text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
