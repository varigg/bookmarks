#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Factory for creating Perplexity clients.

Provides a unified interface for creating either Direct API or MCP-based
Perplexity clients with a common interface.
"""

from typing import Optional, Protocol


class PerplexityClientProtocol(Protocol):
    """Protocol defining the interface all Perplexity clients must implement."""

    def generate_description(self, url: str) -> dict[str, str]:
        """
        Generate title and description for a URL.

        Args:
            url: URL to generate description for

        Returns:
            Dict with 'title' and 'description' keys
        """
        ...

    def get_usage_stats(self) -> dict[str, any]:
        """
        Get usage statistics.

        Returns:
            Dict with 'requests', 'total_tokens', and 'estimated_cost_usd' keys
        """
        ...


class PerplexityClientFactory:
    """Factory for creating Perplexity clients."""

    @staticmethod
    def create_client(
        use_mcp: bool = False, use_markdown: bool = False, api_key: Optional[str] = None
    ) -> PerplexityClientProtocol:
        """
        Create a Perplexity client.

        Args:
            use_mcp: If True, create MCP client. If False, create Direct API client.
            use_markdown: If True, use MarkItDown for content extraction (Direct API only)
            api_key: Optional API key (uses PERPLEXITY_API_KEY env var if not provided)

        Returns:
            A client implementing PerplexityClientProtocol

        Raises:
            ValueError: If API key is not provided or found in environment
            ImportError: If required dependencies are not installed
        """
        if use_mcp:
            try:
                from .perplexity_mcp_client import PerplexityMCPClient

                return PerplexityMCPClient(api_key=api_key)
            except ImportError as e:
                raise ImportError(
                    "MCP client requires 'mcp' package. Install with: uv add mcp"
                ) from e
        elif use_markdown:
            try:
                from .perplexity_client_markdown import PerplexityClientMarkdown

                return PerplexityClientMarkdown(api_key=api_key)
            except ImportError as e:
                raise ImportError(
                    "MarkItDown client requires 'markitdown' package. "
                    "Install with: uv add markitdown"
                ) from e
        else:
            try:
                from .perplexity_client import PerplexityClient

                return PerplexityClient(api_key=api_key)
            except ImportError as e:
                raise ImportError(
                    "Direct API client requires 'requests' and 'beautifulsoup4'. "
                    "Install with: uv add requests beautifulsoup4 lxml"
                ) from e

    @staticmethod
    def get_client_type_name(use_mcp: bool, use_markdown: bool = False) -> str:
        """
        Get a human-readable name for the client type.

        Args:
            use_mcp: Whether MCP client is being used
            use_markdown: Whether MarkItDown client is being used

        Returns:
            String describing the client type
        """
        if use_mcp:
            return "Perplexity MCP"
        elif use_markdown:
            return "Perplexity API (MarkItDown)"
        else:
            return "Perplexity API"


# Convenience function for backward compatibility
def create_perplexity_client(
    use_mcp: bool = False, api_key: Optional[str] = None
) -> PerplexityClientProtocol:
    """
    Create a Perplexity client (convenience wrapper).

    Args:
        use_mcp: If True, use MCP protocol. If False, use direct API.
        api_key: Optional API key

    Returns:
        A client implementing PerplexityClientProtocol
    """
    return PerplexityClientFactory.create_client(use_mcp=use_mcp, api_key=api_key)
