#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Factory for creating LLM services from different providers.

Supports creating services for Perplexity, OpenAI, Anthropic, etc.
with optional content extraction strategies (HTML, Markdown).
"""

from typing import Optional

from .content_extractor import HTMLExtractor, MarkdownExtractor
from .llm_providers import PerplexityProvider
from .llm_service import LLMService


class LLMFactory:
    """Factory for creating LLM clients from different providers."""

    # Supported providers
    PROVIDERS = ["perplexity", "openai", "anthropic"]
    # Supported content extraction formats
    CONTENT_FORMATS = ["html", "markdown"]

    @staticmethod
    def create_client(
        provider: str = "perplexity",
        content_format: str = "html",
        api_key: Optional[str] = None,
    ) -> LLMService:
        """
        Create an LLM service.

        Args:
            provider: LLM provider ('perplexity', 'perplexity-mcp', 'openai', 'anthropic')
            content_format: Content extraction format ('html', 'markdown')
            api_key: Optional API key (uses env var if not provided)

        Returns:
            LLMService instance configured with provider and content extractor

        Raises:
            ValueError: If provider or content_format is not supported
            ImportError: If required dependencies are not installed
        """
        provider = provider.lower()
        content_format = content_format.lower()

        if provider not in LLMFactory.PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Choose from: {', '.join(LLMFactory.PROVIDERS)}"
            )

        if content_format not in LLMFactory.CONTENT_FORMATS:
            raise ValueError(
                f"Unsupported content format: {content_format}. "
                f"Choose from: {', '.join(LLMFactory.CONTENT_FORMATS)}"
            )

        # Select content extractor
        extractor = (
            MarkdownExtractor() if content_format == "markdown" else HTMLExtractor()
        )

        # Create service with appropriate provider
        if provider == "perplexity-mcp":
            # MCP provider - no content extractor needed (MCP server fetches content)
            from .llm_providers import PerplexityMCPProvider
            
            provider_client = PerplexityMCPProvider(api_key=api_key)
            return LLMService(provider=provider_client, content_extractor=None)
        elif provider == "perplexity":
            # Direct API provider with content extractor
            provider_client = PerplexityProvider(api_key=api_key)
            return LLMService(
                provider=provider_client, content_extractor=extractor
            )

        # Future providers
        elif provider == "openai":
            raise NotImplementedError(
                "OpenAI support coming soon. Currently only Perplexity is supported."
            )
        elif provider == "anthropic":
            raise NotImplementedError(
                "Anthropic support coming soon. Currently only Perplexity is supported."
            )
        else:
            raise ValueError(
                f"Unknown provider: {provider}. Supported providers: perplexity, perplexity-mcp"
            )

    @staticmethod
    def get_client_type_name(
        provider: str = "perplexity",
        content_format: str = "html",
    ) -> str:
        """
        Get a human-readable name for the client configuration.

        Args:
            provider: LLM provider name
            content_format: Content extraction format

        Returns:
            String describing the client configuration
        """
        provider_display = provider.replace("-", " ").title()
        
        if provider == "perplexity-mcp":
            return f"{provider_display}"
        
        format_name = "Markdown" if content_format.lower() == "markdown" else "HTML"
        return f"{provider_display} ({format_name})"
