import pytest

from bookmarks.services.llm_client_factory import LLMClientFactory
from bookmarks.services.llm_service import LLMService


def test_create_client_perplexity():
    client = LLMClientFactory.create_client(
        provider="perplexity", content_format="markdown", api_key="dummy"
    )
    assert isinstance(client, LLMService)
    assert client.provider_name == "perplexity"


def test_create_client_openai():
    client = LLMClientFactory.create_client(
        provider="openai", content_format="markdown", api_key="dummy"
    )
    assert isinstance(client, LLMService)
    assert client.provider_name == "openai"


def test_create_client_unsupported_provider():
    with pytest.raises(ValueError, match="Unsupported provider"):
        LLMClientFactory.create_client(provider="unsupported")


def test_create_client_unsupported_format():
    with pytest.raises(ValueError, match="Unsupported content format"):
        LLMClientFactory.create_client(content_format="pdf")


def test_get_client_type_name():
    name = LLMClientFactory.get_client_type_name("perplexity", "html")
    assert "Perplexity (HTML)" in name

    name = LLMClientFactory.get_client_type_name("perplexity-mcp")
    assert "Perplexity Mcp" in name
