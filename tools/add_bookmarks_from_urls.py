"""
Add new bookmarks from a list of URLs.

Usage:
    # Basic import without LLM description
    python add_bookmarks_from_urls.py urls.txt

    # With LLM-generated descriptions
    python add_bookmarks_from_urls.py urls.txt --generate-descriptions

    # With Markdown extraction
    python add_bookmarks_from_urls.py urls.txt --generate-descriptions --content-format markdown

    # With Perplexity MCP
    python add_bookmarks_from_urls.py urls.txt --generate-descriptions --provider perplexity-mcp
"""

import argparse
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from bookmarks.data.model import get_bookmarks, save_bookmark


def test_llm_provider(provider="perplexity", content_format="markdown"):
    """
    Test LLM provider configuration by generating a description for a test URL.

    Args:
        provider: LLM provider to test
        content_format: Content extraction format to use
    """
    from bookmarks.services import LLMClientFactory

    test_url = "https://github.com/python/cpython"
    provider_name = provider  # Store for stats display

    print("=" * 60)
    print("LLM Provider Test")
    print("=" * 60)
    print(f"Provider: {provider}")
    print(f"Content Format: {content_format}")
    print(f"Test URL: {test_url}")
    print()

    try:
        print("Initializing client...")
        client = LLMClientFactory.create_client(provider=provider, content_format=content_format)
        client_name = LLMClientFactory.get_client_type_name(
            provider=provider, content_format=content_format
        )
        print(f"✓ Initialized {client_name} client")
        print()

        print("Generating description...")
        result = client.generate_description(test_url)

        print()
        print("=" * 60)
        print("RESULT:")
        print("=" * 60)
        print(f"Title: {result['title']}")
        print()
        print(f"Description: {result['description']}")
        print()

        # Show usage stats if available
        stats = client.get_usage_stats()
        if stats.get("requests", 0) > 0:
            print("=" * 60)
            provider_display = provider_name.replace("-", " ").title()
            print(f"Usage Statistics ({provider_display}):")
            print(f"  Requests: {stats.get('requests', 0)}")
            print(f"  Total Tokens: {stats.get('total_tokens', 0)}")
            print(f"  Estimated Cost: ${stats.get('estimated_cost_usd', 0.0):.4f}")

        print("=" * 60)
        print("✓ Test successful!")
        print("=" * 60)
        return True

    except Exception as e:
        print()
        print("=" * 60)
        print("✗ Test failed!")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        import traceback

        traceback.print_exc()
        print("=" * 60)
        return False


def read_urls_from_file(filepath):
    """
    Read URLs from a text file.
    Supports raw URLs (one per line) and Markdown links [text](url).
    """
    urls = []
    # Regex for markdown links: [text](url)
    markdown_link_pattern = re.compile(r"\[.*?\]\((.*?)\)")

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Check for markdown link
            match = markdown_link_pattern.search(line)
            if match:
                urls.append(match.group(1))
            else:
                # Assume raw URL
                urls.append(line)

    return urls


def create_basic_bookmark(url):
    """Create a basic bookmark entry without LLM description."""
    return {
        "url": url,
        "title": url,  # Use URL as title initially
        "description": "Imported from URL list. Needs summary.",
        "tags": ["unsummarized"],
        "dateAdded": datetime.now(UTC).isoformat(),
    }


def generate_description_with_llm(url, provider="perplexity", content_format="html"):
    """
    Generate a description for the URL using an LLM.

    Args:
        url: The URL to generate a description for
        provider: LLM provider (perplexity, perplexity-mcp, openai, anthropic)
        content_format: Content extraction format (html, markdown)

    Returns:
        dict with 'title' and 'description' keys
    """
    from bookmarks.services import LLMClientFactory

    try:
        client = LLMClientFactory.create_client(provider=provider, content_format=content_format)
        result = client.generate_description(url)
        return result
    except Exception as e:
        provider_name = LLMClientFactory.get_client_type_name(
            provider=provider, content_format=content_format
        )
        raise RuntimeError(f"{provider_name} error: {e}") from e


def get_next_bookmark_id(bookmarks):
    """Generate the next available bookmark ID."""
    current_ids = [int(bid) for bid in bookmarks if bid.isdigit()]
    return str(max(current_ids, default=-1) + 1)


def add_bookmarks(
    urls,
    generate_descriptions=False,
    provider="perplexity",
    content_format="markdown",
    dry_run=False,
):
    """
    Add bookmarks from a list of URLs.

    Args:
        urls: List of URLs to add
        generate_descriptions: Whether to generate descriptions using LLM
        provider: LLM provider to use (perplexity, perplexity-mcp, openai, anthropic)
        content_format: Content extraction format (html, markdown)
        dry_run: If True, don't actually save bookmarks
    """
    bookmarks = get_bookmarks()
    added_count = 0
    skipped_count = 0
    error_count = 0

    # Initialize LLM client if needed
    llm_client = None
    if generate_descriptions:
        from bookmarks.services import LLMClientFactory

        try:
            llm_client = LLMClientFactory.create_client(
                provider=provider, content_format=content_format
            )
            client_name = LLMClientFactory.get_client_type_name(
                provider=provider, content_format=content_format
            )
            print(f"✓ Initialized {client_name} client")
            print()
        except Exception as e:
            print(f"✗ Failed to initialize {provider} client: {e}")
            print("  Falling back to basic entries")
            print()
            generate_descriptions = False

    # Get existing URLs to avoid duplicates
    existing_urls = {bookmark.get("url") for bookmark in bookmarks.values()}

    total_urls = len(urls)
    for idx, url in enumerate(urls, 1):
        progress = f"[{idx}/{total_urls}]"

        # Skip if URL already exists
        if url in existing_urls:
            print(f"{progress} ⊘ Skipping (already exists): {url}")
            skipped_count += 1
            continue

        # Create bookmark entry
        if generate_descriptions:
            try:
                print(f"{progress} 🔍 Generating description for: {url}")
                llm_data = generate_description_with_llm(url, provider, content_format)
                bookmark = {
                    "url": url,
                    "title": llm_data["title"],
                    "description": llm_data["description"],
                    "tags": ["summarized"],
                    "dateAdded": datetime.now(UTC).isoformat(),
                }
                print(f"         ✓ Title: {llm_data['title'][:60]}...")

                # Add small delay to respect rate limits
                time.sleep(0.5)

            except Exception as e:
                print(f"         ✗ Error: {e}")
                print("         ↳ Using basic entry instead")
                bookmark = create_basic_bookmark(url)
                error_count += 1
        else:
            bookmark = create_basic_bookmark(url)
            print(f"{progress} + Adding: {url}")

        # Save bookmark
        if not dry_run:
            bookmark_id = get_next_bookmark_id(bookmarks)
            save_bookmark(bookmark_id, bookmark)
            bookmarks[bookmark_id] = bookmark  # Update local cache

        added_count += 1

    # Summary
    print(f"\n{'=' * 60}")
    print("Summary:")
    print(f"  Added: {added_count}")
    print(f"  Skipped (duplicates): {skipped_count}")
    if error_count > 0:
        print(f"  Errors (used fallback): {error_count}")
    print(f"  Total URLs processed: {total_urls}")

    # Show LLM usage stats if applicable
    if llm_client and generate_descriptions:
        stats = llm_client.get_usage_stats()
        print("\nLLM Usage Statistics:")
        print(f"  API Requests: {stats['requests']}")
        print(f"  Total Tokens: {stats['total_tokens']}")
        print(f"  Estimated Cost: ${stats['estimated_cost_usd']:.4f}")
        print("  (Your Pro subscription includes $5/month in credits)")

    if dry_run:
        print("\n(DRY RUN - no changes saved)")
    print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(
        description="Add bookmarks from a list of URLs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "url_file",
        type=str,
        nargs="?",
        help="Path to file containing URLs (one per line)",
    )
    parser.add_argument(
        "--generate-descriptions",
        action="store_true",
        help="Generate titles and descriptions using LLM",
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["perplexity", "perplexity-mcp", "openai", "anthropic"],
        default="perplexity",
        help="LLM provider to use (default: perplexity)",
    )
    parser.add_argument(
        "--content-format",
        type=str,
        choices=["html", "markdown"],
        default="markdown",
        help="Content extraction format (default: markdown)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually save bookmarks, just show what would be added",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test LLM provider configuration (ignores url_file)",
    )

    args = parser.parse_args()

    # Handle test mode
    if args.test:
        success = test_llm_provider(provider=args.provider, content_format=args.content_format)
        sys.exit(0 if success else 1)

    # Check if file exists
    url_file = Path(args.url_file)
    if not url_file.exists():
        print(f"Error: File not found: {args.url_file}", file=sys.stderr)
        sys.exit(1)

    # Read URLs
    try:
        urls = read_urls_from_file(url_file)
        if not urls:
            print(f"Warning: No URLs found in {args.url_file}")
            sys.exit(0)

        print(f"Found {len(urls)} URL(s) in {args.url_file}")
        print()

    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    # Add bookmarks
    try:
        add_bookmarks(
            urls,
            generate_descriptions=args.generate_descriptions,
            provider=args.provider,
            content_format=args.content_format,
            dry_run=args.dry_run,
        )
    except Exception as e:
        print(f"Error adding bookmarks: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
