"""
Test script for OpenAI provider.

Usage:
    export OPENAI_API_KEY=sk-your-key
    uv run python tools/test_openai.py
"""

import sys

from bookmarks.services.llm_client_factory import LLMClientFactory


def main():
    """Test OpenAI provider with a sample URL."""
    test_url = "https://flask.palletsprojects.com/"

    print("=" * 60)
    print("OpenAI Provider Test")
    print("=" * 60)
    print("Provider: openai")
    print("Content Format: html")
    print(f"Test URL: {test_url}")
    print()

    try:
        print("Initializing OpenAI client...")
        client = LLMClientFactory.create_client(provider="openai", content_format="html")
        print("✓ Client initialized successfully")
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

        # Show usage stats
        stats = client.get_usage_stats()
        if stats.get("requests", 0) > 0:
            print("=" * 60)
            print("Usage Statistics (OpenAI):")
            print(f"  Requests: {stats.get('requests', 0)}")
            print(f"  Total Tokens: {stats.get('total_tokens', 0)}")
            print(f"  Estimated Cost: ${stats.get('estimated_cost_usd', 0.0):.4f}")

        print("=" * 60)
        print("✓ Test successful!")
        print("=" * 60)
        return True

    except ValueError as e:
        print()
        print("=" * 60)
        print("✗ Configuration Error!")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("Please set your OpenAI API key:")
        print("  export OPENAI_API_KEY=sk-your-key")
        print("=" * 60)
        return False

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


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
