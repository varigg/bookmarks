#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Perplexity Direct API client for generating bookmark descriptions.

This module provides a wrapper around the Perplexity REST API.
It fetches web page content using BeautifulSoup and generates
descriptions using Perplexity's chat completions endpoint.
"""

import json
import os
import time
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .usage_tracker import UsageTracker


class PerplexityClient:
    """Client for interacting with Perplexity API via direct REST calls."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Perplexity client.

        Args:
            api_key: Perplexity API key. If None, reads from PERPLEXITY_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Perplexity API key required. Set PERPLEXITY_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.base_url = "https://api.perplexity.ai"
        self.model = "sonar"  # Default to sonar model for web search
        self.tracker = UsageTracker()

    def fetch_page_content(self, url: str, timeout: int = 10) -> Dict[str, str]:
        """
        Fetch and extract content from a URL.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Dict with 'title', 'text', and 'meta_description' keys
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract title
            title = soup.find("title")
            title_text = title.get_text().strip() if title else urlparse(url).netloc

            # Extract meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            meta_description = meta_desc.get("content", "").strip() if meta_desc else ""

            # Extract main text content
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Get text
            text = soup.get_text()
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)

            # Limit text length for API
            max_chars = 4000
            if len(text) > max_chars:
                text = text[:max_chars] + "..."

            return {
                "title": title_text,
                "text": text,
                "meta_description": meta_description,
            }

        except Exception as e:
            # Return minimal info if fetch fails
            return {
                "title": urlparse(url).netloc,
                "text": f"Unable to fetch content: {str(e)}",
                "meta_description": "",
            }

    def generate_description(
        self,
        url: str,
        page_content: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
    ) -> Dict[str, str]:
        """
        Generate title and description for a URL using Perplexity.

        Args:
            url: URL to generate description for
            page_content: Pre-fetched page content (optional)
            max_retries: Maximum number of retry attempts

        Returns:
            Dict with 'title' and 'description' keys
        """
        # Fetch content if not provided
        if page_content is None:
            page_content = self.fetch_page_content(url)

        # Construct prompt
        prompt = self._build_prompt(url, page_content)

        # Call Perplexity API with retries
        for attempt in range(max_retries):
            try:
                result = self._call_api(prompt)
                return result

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limit
                    wait_time = 2**attempt  # Exponential backoff
                    print(f"  Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                raise
            except Exception:
                if attempt == max_retries - 1:
                    # Last attempt failed, return fallback
                    return self._fallback_description(url, page_content)
                time.sleep(1)

        return self._fallback_description(url, page_content)

    def _build_prompt(self, url: str, page_content: Dict[str, str]) -> str:
        """
        Build the prompt for Perplexity API.

        Args:
            url: URL being analyzed
            page_content: Dict with 'title', 'text', and 'meta_description' keys

        Returns:
            Formatted prompt string for the LLM
        """
        return f"""Given this URL and its content, generate a concise, informative bookmark entry.

URL: {url}
Page Title: {page_content["title"]}
Meta Description: {page_content["meta_description"]}
Content Preview: {page_content["text"][:1000]}

Please provide:
1. A clear, descriptive title (max 100 characters)
2. A 2-3 sentence summary describing what this page is about

Format your response as JSON:
{{
  "title": "...",
  "description": "..."
}}"""

    def _call_api(self, prompt: str) -> Dict[str, str]:
        """
        Make REST API call to Perplexity chat completions endpoint.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            Dict with 'title' and 'description' keys

        Raises:
            requests.exceptions.HTTPError: If API request fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates concise bookmark descriptions. Always respond with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,  # Lower temperature for more consistent output
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

        # Track token usage
        tokens = 0
        if "usage" in data:
            tokens = data["usage"].get("total_tokens", 0)

        # Track request
        estimated_cost = 0.005  # Rough cost per request for sonar
        self.tracker.track_request(tokens, estimated_cost)

        # Parse response
        content = data["choices"][0]["message"]["content"]

        # Try to extract JSON from response
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

        # Fallback: use the content as description
        return {"title": content[:100], "description": content}

    def _fallback_description(
        self, url: str, page_content: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Generate fallback description when API fails.

        Uses the page's existing title and meta description instead of LLM-generated content.

        Args:
            url: URL of the page
            page_content: Dict with 'title', 'text', and 'meta_description' keys

        Returns:
            Dict with 'title' and 'description' keys
        """
        title = page_content["title"]
        description = (
            page_content["meta_description"] or f"Content from {urlparse(url).netloc}"
        )

        return {"title": title[:100], "description": description[:500]}

    def get_usage_stats(self) -> Dict[str, any]:
        """
        Get usage statistics for API calls.

        Returns:
            Dict with 'requests', 'total_tokens', and 'estimated_cost_usd' keys
        """
        return self.tracker.get_current_month_stats()
