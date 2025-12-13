#!/usr/bin/env python3
"""
LLM provider API clients.

Each provider client handles only the API-specific communication logic.
They receive prompts and return raw responses.
"""

import os
from typing import Any, Protocol

import requests


class LLMProvider(Protocol):
    """Protocol defining the interface for LLM provider API clients."""

    def call_api(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """
        Make API call to the LLM provider.

        Args:
            system_prompt: System message/instruction
            user_prompt: User's prompt/question

        Returns:
            Dict with provider-specific response structure
        """
        ...


class PerplexityProvider:
    """API client for Perplexity."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize Perplexity provider.

        Args:
            api_key: API key (reads from PERPLEXITY_API_KEY env var if None)
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Perplexity API key required. Set PERPLEXITY_API_KEY environment variable."
            )
        self.base_url = "https://api.perplexity.ai"
        self.model = "sonar"

    def call_api(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """
        Call Perplexity chat completions API.

        Args:
            system_prompt: System message
            user_prompt: User prompt

        Returns:
            Dict with 'content' (response text) and 'usage' (token stats) keys
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 300,
        }

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()

        return {
            "content": data["choices"][0]["message"]["content"],
            "usage": data.get("usage", {}),
        }


class OpenAIProvider:
    """API client for OpenAI."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize OpenAI provider.

        Args:
            api_key: API key (reads from OPENAI_API_KEY env var if None)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
        self.base_url = "https://api.openai.com/v1"
        self.model = "gpt-4o-mini"  # Cost-effective model for summarization

    def call_api(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """
        Call OpenAI chat completions API.

        Args:
            system_prompt: System message
            user_prompt: User prompt

        Returns:
            Dict with 'content' (response text) and 'usage' (token stats) keys
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 300,
        }

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()

        return {
            "content": data["choices"][0]["message"]["content"],
            "usage": data.get("usage", {}),
        }


class AnthropicProvider:
    """API client for Anthropic."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize Anthropic provider.

        Args:
            api_key: API key (reads from ANTHROPIC_API_KEY env var if None)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable."
            )
        self.base_url = "https://api.anthropic.com/v1"
        self.model = "claude-3-5-haiku-20241022"  # Fast and cost-effective model
        self.api_version = "2023-06-01"  # API version for Messages API

    def call_api(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """
        Call Anthropic messages API.

        Args:
            system_prompt: System message
            user_prompt: User prompt

        Returns:
            Dict with 'content' (response text) and 'usage' (token stats) keys
        """
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json",
        }

        # Build payload according to Anthropic Messages API spec
        payload = {
            "model": self.model,
            "max_tokens": 300,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        # Add system prompt if provided
        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(
            f"{self.base_url}/messages",
            headers=headers,
            json=payload,
            timeout=30,
        )

        # Add better error handling
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            error_detail = ""
            try:
                error_detail = f" - {response.json()}"
            except (ValueError, requests.JSONDecodeError):
                error_detail = f" - {response.text}"
            raise requests.HTTPError(f"{e}{error_detail}", response=response) from e

        data = response.json()

        # Extract text content from response
        content_text = ""
        if "content" in data and len(data["content"]) > 0:
            content_text = data["content"][0].get("text", "")

        return {
            "content": content_text,
            "usage": data.get("usage", {}),
        }


class PerplexityMCPProvider:
    """API client for Perplexity using MCP protocol."""

    def __init__(self, api_key: str | None = None):
        """
        Initialize Perplexity MCP provider.

        Args:
            api_key: API key (reads from PERPLEXITY_API_KEY env var if None)
        """
        import asyncio

        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Perplexity API key required. Set PERPLEXITY_API_KEY environment variable."
            )

        # Store MCP modules for later use
        self._asyncio = asyncio
        self._ClientSession = ClientSession
        self._StdioServerParameters = StdioServerParameters
        self._stdio_client = stdio_client

    def call_api(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """
        Call Perplexity via MCP protocol.

        Note: MCP server fetches the URL content itself, so we just pass the URL.
        The system_prompt is ignored since MCP server has its own behavior.

        Args:
            system_prompt: Ignored (MCP server behavior is predefined)
            user_prompt: Should contain the URL and request

        Returns:
            Dict with 'content' (response text) and 'usage' (empty dict) keys
        """
        return self._asyncio.run(self._call_mcp_async(user_prompt))

    async def _call_mcp_async(self, user_prompt: str) -> dict[str, Any]:
        """Async implementation of MCP call."""

        # Configure the Perplexity MCP server
        server_params = self._StdioServerParameters(
            command="npx",
            args=["-y", "@perplexity-ai/mcp-server"],
            env={
                "PERPLEXITY_API_KEY": self.api_key,  # type: ignore[dict-item]
                "PERPLEXITY_MODEL": "sonar",
            },
        )

        async with (
            self._stdio_client(server_params) as (read, write),
            self._ClientSession(read, write) as session,
        ):
            await session.initialize()

            # Build messages - MCP expects this format
            messages = [{"role": "user", "content": user_prompt}]

            # Call the perplexity_ask tool
            result = await session.call_tool("perplexity_ask", arguments={"messages": messages})

            # Extract text from MCP result
            text_parts = []
            if hasattr(result, "content") and isinstance(result.content, list):
                for item in result.content:
                    # Use getattr to safely access text attribute
                    text = getattr(item, "text", None)
                    if text is not None:
                        text_parts.append(str(text))
                    else:
                        text_parts.append(str(item))

            content = "\n".join(text_parts) if text_parts else str(result)

            return {
                "content": content,
                "usage": {},  # MCP doesn't provide token usage
            }
