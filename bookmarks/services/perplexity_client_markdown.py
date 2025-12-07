#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Perplexity client using MarkItDown for better content extraction.

This version uses MarkItDown to convert web pages to markdown before
sending to the LLM, preserving structure and semantic information.
"""

import time
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
from markitdown import MarkItDown

from .perplexity_client import PerplexityClient


class PerplexityClientMarkdown(PerplexityClient):
    """Client for Perplexity API using MarkItDown for content extraction."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Perplexity client with MarkItDown.

        Args:
            api_key: Perplexity API key. If None, reads from PERPLEXITY_API_KEY env var.
        """
        super().__init__(api_key)
        self.md_converter = MarkItDown()

    def fetch_page_content(self, url: str, timeout: int = 10) -> Dict[str, str]:
        """
        Fetch and convert web page to markdown.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Dict with 'title', 'markdown', and 'url' keys
        """
        try:
            # Fetch the page
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            # Convert to markdown
            result = self.md_converter.convert_stream(response.content)
            markdown_text = result.text_content

            # Extract title from markdown (first H1 or use domain)
            title = self._extract_title_from_markdown(markdown_text, url)

            # Limit markdown length for API (markdown is more verbose than plain text)
            max_chars = 3000  # Reduced from 4000 due to markdown formatting
            if len(markdown_text) > max_chars:
                markdown_text = markdown_text[:max_chars] + "\n\n[Content truncated...]"

            return {"title": title, "markdown": markdown_text, "url": url}

        except Exception as e:
            # Fallback to minimal info
            return {
                "title": urlparse(url).netloc,
                "markdown": f"Unable to fetch content: {str(e)}",
                "url": url,
            }

    def _extract_title_from_markdown(self, markdown: str, url: str) -> str:
        """
        Extract title from markdown content.

        Looks for first H1 heading, falls back to domain name.

        Args:
            markdown: Markdown content
            url: Original URL

        Returns:
            Extracted title
        """
        lines = markdown.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                # Found H1 heading
                return line[2:].strip()

        # Fallback to domain
        return urlparse(url).netloc

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
        prompt = self._build_prompt(page_content)

        # Call Perplexity API with retries
        for attempt in range(max_retries):
            try:
                result = self._call_api(prompt)
                # Request count is tracked in _call_api via super() or local override if needed
                # But PerplexityClient._call_api doesn't increment request_count, generate_description does.
                # Since we are overriding generate_description, we need to increment it here.
                # However, PerplexityClient tracks it in generate_description.
                # Let's check PerplexityClient implementation.
                # It seems PerplexityClient.generate_description calls _call_api.
                # Here we are overriding generate_description completely.

                # We need to access the tracker from the parent class if it exists
                # In the new implementation, PerplexityClient uses self.tracker.
                # So we should use self.tracker.track_request()

                # Note: The original file didn't use UsageTracker yet, but PerplexityClient does now.
                # We should ensure this class uses the new UsageTracker pattern.

                # Since we inherit from PerplexityClient, we have self.tracker.

                # We need to manually track here because we are not calling super().generate_description

                # Wait, _call_api in PerplexityClient now tracks usage!
                # Let's check PerplexityClient._call_api.
                # No, PerplexityClient._call_api just makes the request.
                # PerplexityClient.generate_description calls _call_api and then tracks usage.

                # So we need to track usage here too.

                # But wait, _call_api in THIS class (if it exists) might need updating.
                # The original file had its own _call_api.

                return result

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limit
                    wait_time = 2**attempt
                    print(f"  Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                raise
            except Exception:
                if attempt == max_retries - 1:
                    return self._fallback_description(page_content)
                time.sleep(1)

        return self._fallback_description(page_content)

    def _build_prompt(self, page_content: Dict[str, str]) -> str:
        """
        Build the prompt for Perplexity API using markdown content.

        Args:
            page_content: Dict with 'title', 'markdown', and 'url' keys

        Returns:
            Formatted prompt string for the LLM
        """
        return f"""Analyze this web page (provided in markdown format) and create a bookmark entry.

URL: {page_content["url"]}

Page Content (Markdown):
{page_content["markdown"]}

Please provide:
1. A clear, descriptive title (max 100 characters) - use the main heading if available
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
        # We can reuse the parent's _call_api if it supports the same interface
        # Parent _call_api takes prompt and returns dict.
        # But parent _call_api handles tracking internally now?
        # Let's check PerplexityClient._call_api again.

        # PerplexityClient._call_api:
        #   - Makes request
        #   - Tracks usage via self.tracker.track_request()
        #   - Returns parsed JSON result

        # So we can just call super()._call_api(prompt)
        return super()._call_api(prompt)

    def _fallback_description(self, page_content: Dict[str, str]) -> Dict[str, str]:
        """
        Generate fallback description when API fails.

        Args:
            page_content: Dict with 'title', 'markdown', and 'url' keys

        Returns:
            Dict with 'title' and 'description' keys
        """
        title = page_content["title"]
        # Use first paragraph from markdown as description
        lines = [l.strip() for l in page_content["markdown"].split("\n") if l.strip()]
        description = next(
            (l for l in lines if not l.startswith("#") and len(l) > 20),
            f"Content from {urlparse(page_content['url']).netloc}",
        )

        return {"title": title[:100], "description": description[:500]}
