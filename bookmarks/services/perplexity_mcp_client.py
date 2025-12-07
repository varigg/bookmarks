#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP-based client for Perplexity using the official MCP Python SDK.

This provides an alternative to the direct API approach, using the
Model Context Protocol to interact with Perplexity.
"""

import asyncio
import json
import os
from typing import Dict, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .usage_tracker import UsageTracker


class PerplexityMCPClient:
    """Client for Perplexity using MCP protocol."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Perplexity MCP client.

        Args:
            api_key: Perplexity API key. If None, reads from PERPLEXITY_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Perplexity API key required. Set PERPLEXITY_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.tracker = UsageTracker()

    def _get_session(self):
        """Create and return an MCP session."""
        # Configure the Perplexity MCP server
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@perplexity-ai/mcp-server"],
            env={
                "PERPLEXITY_API_KEY": self.api_key,
                "PERPLEXITY_MODEL": "sonar",  # Default model
            },
        )

        # Create client session
        return stdio_client(server_params)

    async def generate_description_async(self, url: str) -> Dict[str, str]:
        """
        Generate description using MCP.

        Args:
            url: URL to generate description for

        Returns:
            Dict with 'title' and 'description' keys
        """
        async with self._get_session() as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()

                # List available tools
                tools = await session.list_tools()
                print(f"Available MCP tools: {[t.name for t in tools.tools]}")

                # Build the messages array (required format)
                messages = [
                    {
                        "role": "user",
                        "content": f"""Analyze this URL and provide a bookmark entry: {url}

Please respond with JSON in this exact format:
{{
  "title": "A concise, descriptive title (max 100 characters)",
  "description": "A 2-3 sentence summary of what this page is about"
}}""",
                    }
                ]

                # Call the perplexity_ask tool with correct format
                result = await session.call_tool(
                    "perplexity_ask", arguments={"messages": messages}
                )

                # Track request (MCP doesn't give token usage easily, so we estimate)
                estimated_cost = 0.005
                self.tracker.track_request(0, estimated_cost)

                # Parse the result
                return self._parse_mcp_result(result, url)

    def generate_description(self, url: str) -> Dict[str, str]:
        """
        Synchronous wrapper for generate_description_async.

        Args:
            url: URL to generate description for

        Returns:
            Dict with 'title' and 'description' keys
        """
        return asyncio.run(self.generate_description_async(url))

    def _parse_mcp_result(self, result, url: str) -> Dict[str, str]:
        """Parse MCP tool result into title and description."""
        try:
            # MCP returns a list of content items
            if hasattr(result, "content") and isinstance(result.content, list):
                # Extract text from TextContent objects
                text_parts = []
                for item in result.content:
                    if hasattr(item, "text"):
                        text_parts.append(item.text)
                    else:
                        text_parts.append(str(item))

                full_text = "\n".join(text_parts)

                # Try to parse as JSON first
                try:
                    # Look for JSON in the response
                    start = full_text.find("{")
                    end = full_text.rfind("}") + 1
                    if start >= 0 and end > start:
                        json_str = full_text[start:end]
                        data = json.loads(json_str)
                        return {
                            "title": data.get("title", url)[:100],
                            "description": data.get("description", full_text)[:500],
                        }
                except json.JSONDecodeError:
                    pass

                # Fallback: use first 100 chars as title, rest as description
                lines = full_text.split("\n")
                title = lines[0] if lines else url
                description = (
                    full_text if len(full_text) > 100 else f"Content from {url}"
                )

                return {"title": title[:100], "description": description[:500]}

            # Fallback for unexpected format
            content_str = str(result)
            return {"title": content_str[:100], "description": content_str[:500]}

        except Exception as e:
            return {"title": url, "description": f"Error parsing MCP result: {e}"}

    def get_usage_stats(self) -> Dict[str, any]:
        """Get usage statistics."""
        return self.tracker.get_current_month_stats()


# Convenience function for backward compatibility
def create_perplexity_client(use_mcp: bool = False, api_key: Optional[str] = None):
    """
    Create a Perplexity client.

    Args:
        use_mcp: If True, use MCP protocol. If False, use direct API.
        api_key: Optional API key

    Returns:
        PerplexityMCPClient or PerplexityClient instance
    """
    if use_mcp:
        return PerplexityMCPClient(api_key)
    else:
        from .perplexity_client import PerplexityClient

        return PerplexityClient(api_key)
