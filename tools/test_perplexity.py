#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to compare Direct API vs MCP approaches for Perplexity.

Usage:
    # Test direct API
    python test_perplexity.py --method direct

    # Test MCP
    python test_perplexity.py --method mcp

    # Test both
    python test_perplexity.py --method both
"""

import argparse
import time

import pytest


@pytest.fixture
def url():
    """Fixture providing a test URL."""
    return "https://example.com"


def test_direct_api(url: str):
    """Test the direct API approach."""
    print("=" * 60)
    print("Testing Direct API Approach")
    print("=" * 60)

    try:
        from perplexity_client import PerplexityClient

        print("✓ Imported PerplexityClient")

        client = PerplexityClient()
        print("✓ Initialized client")

        print(f"\nFetching and analyzing: {url}")
        start_time = time.time()

        result = client.generate_description(url)

        elapsed = time.time() - start_time

        print(f"\n✓ Success! (took {elapsed:.2f}s)")
        print(f"\nTitle: {result['title']}")
        print(f"\nDescription: {result['description']}")

        stats = client.get_usage_stats()
        print("\nUsage Stats:")
        print(f"  Requests: {stats['requests']}")
        print(f"  Tokens: {stats['total_tokens']}")
        print(f"  Cost: ${stats['estimated_cost_usd']:.4f}")

        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_mcp(url: str):
    """Test the MCP approach."""
    print("=" * 60)
    print("Testing MCP Approach")
    print("=" * 60)

    try:
        from perplexity_mcp_client import PerplexityMCPClient

        print("✓ Imported PerplexityMCPClient")

        client = PerplexityMCPClient()
        print("✓ Initialized MCP client")

        print(f"\nFetching and analyzing: {url}")
        print("(This will spawn an MCP server subprocess...)")
        start_time = time.time()

        result = client.generate_description(url)

        elapsed = time.time() - start_time

        print(f"\n✓ Success! (took {elapsed:.2f}s)")
        print(f"\nTitle: {result['title']}")
        print(f"\nDescription: {result['description']}")

        stats = client.get_usage_stats()
        print("\nUsage Stats:")
        print(f"  Requests: {stats['requests']}")
        print(f"  Cost: ${stats['estimated_cost_usd']:.4f}")

        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Test Perplexity integration methods")
    parser.add_argument(
        "--method",
        choices=["direct", "mcp", "both"],
        default="both",
        help="Which method to test",
    )
    parser.add_argument(
        "--url", default="https://github.com/python/cpython", help="URL to test with"
    )

    args = parser.parse_args()

    print(f"\nTest URL: {args.url}\n")

    results = {}

    if args.method in ["direct", "both"]:
        results["direct"] = test_direct_api(args.url)
        print()

    if args.method in ["mcp", "both"]:
        if args.method == "both":
            print("\n" + "=" * 60)
            print()
        results["mcp"] = test_mcp(args.url)
        print()

    # Summary
    if args.method == "both":
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Direct API: {'✓ PASS' if results.get('direct') else '✗ FAIL'}")
        print(f"MCP:        {'✓ PASS' if results.get('mcp') else '✗ FAIL'}")
        print()

        if all(results.values()):
            print("🎉 Both methods work!")
        elif any(results.values()):
            print("⚠️  One method failed - check errors above")
        else:
            print("✗ Both methods failed - check configuration")


if __name__ == "__main__":
    main()
