#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Content extraction layer for converting web pages to structured content.

Provides multiple extraction strategies (BeautifulSoup HTML, MarkItDown markdown)
allowing LLM clients to be independent of content format.
"""

from io import BytesIO
from typing import Dict, Protocol
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from markitdown import MarkItDown


class ContentExtractor(Protocol):
    """Protocol defining the interface for content extraction strategies."""

    def extract(self, url: str, timeout: int = 10) -> Dict[str, str]:
        """
        Extract content from a URL.

        Args:
            url: URL to fetch and extract
            timeout: Request timeout in seconds

        Returns:
            Dict with extracted content (keys vary by implementation)
        """
        ...


class HTMLExtractor:
    """Extract plain text content from HTML using BeautifulSoup."""

    def extract(self, url: str, timeout: int = 10) -> Dict[str, str]:
        """
        Extract plain text content from a URL using BeautifulSoup.

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
            if meta_desc and meta_desc.get("content"):
                content = meta_desc["content"]
                meta_description = content[0].strip() if isinstance(content, list) else content.strip()
            else:
                meta_description = ""

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


class MarkdownExtractor:
    """Extract markdown content from web pages using MarkItDown."""

    def __init__(self):
        """Initialize markdown extractor with MarkItDown converter."""
        self.md_converter = MarkItDown()

    def extract(self, url: str, timeout: int = 10) -> Dict[str, str]:
        """
        Extract and convert web page to markdown.

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
            result = self.md_converter.convert_stream(BytesIO(response.content))
            markdown_text = result.text_content

            # Extract title from markdown (first H1 or use domain)
            title = self._extract_title_from_markdown(markdown_text, url)

            # Limit markdown length for API (markdown is more verbose than plain text)
            max_chars = 3000
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

    @staticmethod
    def _extract_title_from_markdown(markdown: str, url: str) -> str:
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
