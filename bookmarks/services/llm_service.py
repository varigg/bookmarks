#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Service - orchestrates content extraction, prompt building, and LLM API calls.

This service uses composition: it's configured with a content extractor and an LLM provider,
then handles all the common logic (retry, fallback, prompt building, response parsing).
"""

import json
import time
from typing import Any, Dict, Optional

import requests

from .content_extractor import ContentExtractor
from .llm_providers import LLMProvider
from .usage_tracker import UsageTracker


class LLMService:
    """Service that orchestrates content extraction and LLM generation."""

    def __init__(
        self,
        provider: LLMProvider,
        content_extractor: Optional[ContentExtractor] = None,
        provider_name: str = "unknown",
    ):
        """
        Initialize LLM service.

        Args:
            provider: LLM provider client (e.g., PerplexityProvider)
            content_extractor: Content extraction strategy (None for providers that fetch content themselves like MCP)
            provider_name: Name of the provider for usage tracking (e.g., "perplexity", "openai")
        """
        self.provider = provider
        self.content_extractor = content_extractor
        self.provider_name = provider_name
        self.tracker = UsageTracker(provider=provider_name)

    def generate_description(
        self,
        url: str,
        page_content: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
    ) -> Dict[str, str]:
        """
        Generate title and description for a URL.

        Args:
            url: URL to generate description for
            page_content: Pre-fetched content (optional, will fetch if None and extractor available)
            max_retries: Maximum retry attempts

        Returns:
            Dict with 'title' and 'description' keys
        """
        # Step 1: Extract content from URL (if extractor is configured)
        if page_content is None and self.content_extractor is not None:
            page_content = self.content_extractor.extract(url)

        # For MCP providers, page_content may remain None (they fetch URLs themselves)
        if page_content is None:
            page_content = {}

        # Step 2: Build prompts
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(url, page_content)

        # Step 3: Call LLM with retry logic
        for attempt in range(max_retries):
            try:
                response = self.provider.call_api(system_prompt, user_prompt)

                # Track usage
                usage = response.get("usage", {})
                tokens = usage.get("total_tokens", 0)
                estimated_cost = self._estimate_cost(tokens)
                self.tracker.track_request(tokens, estimated_cost)

                # Parse response
                return self._parse_response(response["content"], url, page_content)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limit
                    wait_time = 2**attempt
                    print(f"  Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                raise
            except Exception:
                if attempt == max_retries - 1:
                    return self._fallback_description(url, page_content)
                time.sleep(1)

        return self._fallback_description(url, page_content)

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        stats = self.tracker.get_current_month_stats()
        # Return with consistent key names for backward compatibility
        return {
            "requests": stats.get("requests", 0),
            "total_tokens": stats.get("tokens", 0),
            "estimated_cost_usd": stats.get("cost", 0.0),
        }

    @staticmethod
    def _build_system_prompt() -> str:
        """Build system prompt for bookmark generation."""
        return (
            "You are a helpful assistant that creates concise bookmark descriptions. "
            "Always respond with valid JSON."
        )

    @staticmethod
    def _build_user_prompt(url: str, content: Dict[str, str]) -> str:
        """
        Build user prompt based on extracted content.

        Args:
            url: The URL
            content: Extracted page content (format depends on extractor)

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            "Given this URL and its content, generate a concise, informative bookmark entry.",
            "",
            f"URL: {url}",
        ]

        # Add content based on available keys
        if "title" in content:
            prompt_parts.append(f"Page Title: {content['title']}")
        if "meta_description" in content:
            prompt_parts.append(f"Meta Description: {content['meta_description']}")
        if "text" in content:
            prompt_parts.append(f"Content Preview: {content['text'][:1000]}")
        if "markdown" in content:
            prompt_parts.append(f"Content (Markdown):\n{content['markdown'][:1500]}")

        prompt_parts.extend(
            [
                "",
                "Please provide:",
                "1. A clear, descriptive title (max 100 characters)",
                "2. A 2-3 sentence summary describing what this page is about",
                "",
                "Format your response as JSON:",
                "{",
                '  "title": "...",',
                '  "description": "..."',
                "}",
            ]
        )

        return "\n".join(prompt_parts)

    @staticmethod
    def _parse_response(
        content: str, url: str, page_content: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Parse LLM response into title and description.

        Args:
            content: Raw response from LLM
            url: Original URL (fallback)
            page_content: Extracted content (fallback)

        Returns:
            Dict with 'title' and 'description' keys
        """
        try:
            # Look for JSON in the response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                result = json.loads(json_str)
                return {
                    "title": result.get("title", "").strip(),
                    "description": result.get("description", "").strip(),
                }
        except json.JSONDecodeError:
            pass

        # Fallback: use content as description
        return {"title": content[:100], "description": content}

    @staticmethod
    def _fallback_description(url: str, content: Dict[str, str]) -> Dict[str, str]:
        """
        Generate fallback description when LLM fails.

        Args:
            url: The URL
            content: Extracted content

        Returns:
            Dict with 'title' and 'description' keys
        """
        title = content.get("title", url)
        description = (
            content.get("meta_description", "") or content.get("text", "")[:200]
        )

        return {
            "title": title[:100] if title else url,
            "description": description[:500] if description else "",
        }

    @staticmethod
    def _estimate_cost(tokens: int) -> float:
        """
        Estimate cost based on token usage.

        Args:
            tokens: Number of tokens used

        Returns:
            Estimated cost in USD
        """
        # Rough estimate for Perplexity sonar model
        return 0.005 if tokens > 0 else 0.005
