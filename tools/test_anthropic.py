"""
Test script for Anthropic provider.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-your-key
    uv run python tools/test_anthropic.py
"""

import sys

from bookmarks.services.llm_client_factory import LLMClientFactory


def main():
    """Test Anthropic provider with a sample URL."""
    test_url = "https://flask.palletsprojects.com/"

    print("=" * 60)
    print("Anthropic Provider Test")
    print("=" * 60)
    print("Provider: anthropic")
    print("Content Format: html")
    print(f"Test URL: {test_url}")
    print()

    try:
        print("Initializing Anthropic client...")
        client = LLMClientFactory.create_client(provider="anthropic", content_format="html")
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
            print("Usage Statistics (Anthropic):")
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
        print("Please set your Anthropic API key:")
        print("  export ANTHROPIC_API_KEY=sk-ant-your-key")
        print()
        print("Get your API key from: https://console.anthropic.com/settings/keys")
        print("=" * 60)
        return False

    except Exception as e:
        print()
        print("=" * 60)
        print("✗ Test failed!")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        error_str = str(e).lower()
        if "credit balance" in error_str or "billing" in error_str:
            print("Your Anthropic account needs credits to use the API.")
            print()
            print("Solutions:")
            print("  - Add credits at: https://console.anthropic.com/settings/billing")
            print("  - Or use a different provider (Perplexity or OpenAI)")
            print()
        elif "400" in error_str or "bad request" in error_str:
            print("Common causes of 400 Bad Request:")
            print("  1. Invalid API key format")
            print("  2. API key doesn't have access to claude-3-5-haiku-20241022 model")
            print("  3. Insufficient credits (check billing)")
            print()
            print("Solutions:")
            print("  - Verify your API key is correct")
            print("  - Check your Anthropic account billing")
            print("  - Try a different model (edit llm_providers.py)")
            print()
        import traceback

        traceback.print_exc()
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
