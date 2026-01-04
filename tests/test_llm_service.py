from unittest.mock import MagicMock, patch

import pytest

from bookmarks.services.llm_service import LLMService


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.call_api.return_value = {
        "content": '{"title": "Test Title", "description": "Test Description"}',
        "usage": {"total_tokens": 100},
    }
    provider.estimate_cost.return_value = 0.05
    provider.get_default_model.return_value = "test-model"
    return provider


@pytest.fixture
def mock_extractor():
    extractor = MagicMock()
    extractor.extract.return_value = {"title": "Page Title", "text": "Page content"}
    return extractor


def test_generate_description_success(mock_provider, mock_extractor):
    service = LLMService(
        provider=mock_provider, content_extractor=mock_extractor, provider_name="test"
    )

    # Mock UsageTracker to avoid file I/O during this test
    with patch.object(service, "tracker") as mock_tracker:
        result = service.generate_description("https://example.com")

        assert result["title"] == "Test Title"
        assert result["description"] == "Test Description"
        mock_extractor.extract.assert_called_once()
        mock_provider.call_api.assert_called_once()
        mock_tracker.track_request.assert_called_once()


def test_generate_description_retry_logic(mock_provider, mock_extractor):
    service = LLMService(provider=mock_provider, content_extractor=mock_extractor)

    # Fail twice, succeed on third attempt
    mock_provider.call_api.side_effect = [
        Exception("First fail"),
        Exception("Second fail"),
        {"content": '{"title": "Success", "description": "Desc"}', "usage": {}},
    ]

    with (
        patch("time.sleep"),
        patch.object(service, "tracker"),
    ):  # Special patch to avoid waiting and disk I/O
        result = service.generate_description("https://example.com")

    assert result["title"] == "Success"
    assert mock_provider.call_api.call_count == 3


def test_generate_description_fallback(mock_provider, mock_extractor):
    service = LLMService(provider=mock_provider, content_extractor=mock_extractor)

    # Always fail
    mock_provider.call_api.side_effect = Exception("Permanent fail")

    with patch("time.sleep"), patch.object(service, "tracker"):
        result = service.generate_description("https://example.com")

    # Should use fallback from extractor content
    assert result["title"] == "Page Title"
    assert "Page content" in result["description"]


def test_parse_response_json_in_markdown(mock_provider):
    service = LLMService(provider=mock_provider)
    content = (
        "Here is the JSON:\n```json\n"
        + '{"title": "JSON Title", "description": "JSON Desc"}'
        + "\n```"
    )

    result = service._parse_response(content, "url", {})
    assert result["title"] == "JSON Title"
    assert result["description"] == "JSON Desc"


def test_parse_response_malformed(mock_provider):
    service = LLMService(provider=mock_provider)
    content = "This is not JSON at all."

    result = service._parse_response(content, "url", {})
    assert result["title"] == content[:100]
    assert result["description"] == content
