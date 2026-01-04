from unittest.mock import MagicMock, patch

import requests

from bookmarks.services.content_extractor import HTMLExtractor, MarkdownExtractor


def test_html_extractor_success():
    extractor = HTMLExtractor()
    url = "https://example.com"
    html_content = """
    <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="This is a test description">
        </head>
        <body>
            <nav>Navigation</nav>
            <h1>Main Title</h1>
            <p>Some content text.</p>
            <footer>Footer</footer>
        </body>
    </html>
    """

    mock_response = MagicMock()
    mock_response.text = html_content
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        result = extractor.extract(url)

    assert result["title"] == "Test Page"
    assert "Some content text." in result["text"]
    assert "Navigation" not in result["text"]
    assert result["meta_description"] == "This is a test description"


def test_html_extractor_failure():
    extractor = HTMLExtractor()
    url = "https://example.com"

    with patch(
        "requests.get", side_effect=requests.exceptions.RequestException("Connection error")
    ):
        result = extractor.extract(url)

    assert result["title"] == "example.com"
    assert "Unable to fetch content" in result["text"]
    assert result["meta_description"] == ""


def test_markdown_extractor_success():
    extractor = MarkdownExtractor()
    url = "https://example.com"

    mock_response = MagicMock()
    mock_response.content = b"<html><body><h1>Test Markdown</h1><p>Content</p></body></html>"
    mock_response.status_code = 200

    # Mocking self.md_converter.convert_stream
    mock_result = MagicMock()
    mock_result.text_content = "# Test Markdown\n\nContent"

    with (
        patch("requests.get", return_value=mock_response),
        patch.object(extractor.md_converter, "convert_stream", return_value=mock_result),
    ):
        result = extractor.extract(url)

    assert result["title"] == "Test Markdown"
    assert "# Test Markdown" in result["markdown"]
    assert result["url"] == url


def test_markdown_extractor_fallback_title():
    extractor = MarkdownExtractor()
    url = "https://example.com/page"

    # Content without H1
    markdown = "Just some text without a heading."
    title = extractor._extract_title_from_markdown(markdown, url)

    assert title == "example.com"


def test_markdown_extractor_custom_max_chars():
    extractor = MarkdownExtractor(max_chars=10)
    url = "https://example.com"

    mock_response = MagicMock()
    mock_response.content = b"Some long content"
    mock_response.status_code = 200

    mock_result = MagicMock()
    mock_result.text_content = "This is a very long string that should be truncated."

    with (
        patch("requests.get", return_value=mock_response),
        patch.object(extractor.md_converter, "convert_stream", return_value=mock_result),
    ):
        result = extractor.extract(url)

    assert result["markdown"].startswith("This is a ")
    assert "[Content truncated...]" in result["markdown"]
    assert len(result["markdown"]) > 10  # 10 chars + truncation message


def test_extract_title_variants():
    extractor = MarkdownExtractor()
    url = "https://example.com"

    assert extractor._extract_title_from_markdown("# My Title", url) == "My Title"
    assert extractor._extract_title_from_markdown("## No H1\n# My H1 Title", url) == "My H1 Title"
    assert extractor._extract_title_from_markdown("Title: Page Title", url) == "Page Title"
    assert extractor._extract_title_from_markdown("No title here", url) == "example.com"
