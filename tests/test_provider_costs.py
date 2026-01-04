import pytest

from bookmarks.services.llm_providers import (
    AnthropicProvider,
    OpenAIProvider,
    PerplexityMCPProvider,
    PerplexityProvider,
)


def test_perplexity_provider_cost():
    provider = PerplexityProvider(api_key="dummy")
    # Should be flat 0.005 if tokens > 0
    assert provider.estimate_cost(100) == 0.005
    assert provider.estimate_cost(0) == 0.0


def test_openai_provider_cost():
    provider = OpenAIProvider(api_key="dummy")
    # $0.30 per 1M tokens
    assert provider.estimate_cost(1_000_000) == 0.30
    assert provider.estimate_cost(500_000) == 0.15


def test_anthropic_provider_cost():
    provider = AnthropicProvider(api_key="dummy")
    # $0.50 per 1M tokens
    assert provider.estimate_cost(1_000_000) == 0.50
    assert provider.estimate_cost(200_000) == 0.10


def test_perplexity_mcp_provider_cost():
    # PerplexityMCPProvider imports mcp which might not be installed in all envs,
    # but here we just want to test the method if it's already defined.
    try:
        provider = PerplexityMCPProvider(api_key="dummy")
        assert provider.estimate_cost(100) == 0.0
    except ImportError:
        pytest.skip("mcp not installed")


def test_provider_default_models():
    assert PerplexityProvider(api_key="dummy").get_default_model() == "sonar"
    assert OpenAIProvider(api_key="dummy").get_default_model() == "gpt-4o-mini"
    assert AnthropicProvider(api_key="dummy").get_default_model() == "claude-3-5-haiku-20241022"
