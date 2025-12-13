import unittest
from unittest.mock import MagicMock, patch

from bookmarks import create_app
from bookmarks.core.exceptions import LLMGenerationError


class TestAutofillRoute(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.app.config["TESTING"] = True

    @patch("bookmarks.web.routes.get_bookmark_service")
    def test_autofill_success(self, mock_get_service):
        # Mock the service
        mock_service = MagicMock()
        mock_service.generate_metadata.return_value = {
            "title": "Test Title",
            "description": "Test Description",
        }
        mock_get_service.return_value = mock_service

        # Make request
        response = self.client.post("/bookmarks/autofill", data={"url": "https://example.com"})

        # Debug: print response details
        print(f"Status code: {response.status_code}")
        print(f"Response data: {response.data.decode('utf-8', errors='ignore')[:500]}")

        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'value="https://example.com/"', response.data)
        self.assertIn(b'value="Test Title"', response.data)
        self.assertIn(b"Test Description", response.data)

        # Verify service was called
        mock_service.generate_metadata.assert_called_once_with("https://example.com/")

    @patch("bookmarks.web.routes.get_bookmark_service")
    def test_autofill_error(self, mock_get_service):
        # Mock error
        mock_service = MagicMock()
        mock_service.generate_metadata.side_effect = LLMGenerationError(
            url="https://example.com", original_error=Exception("API Error")
        )
        mock_get_service.return_value = mock_service

        # Make request
        response = self.client.post("/bookmarks/autofill", data={"url": "https://example.com"})

        # Verify response (should still render page but with error message)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Error generating description", response.data)
        self.assertIn(b'value="https://example.com/"', response.data)

    def test_autofill_no_url(self):
        response = self.client.post("/bookmarks/autofill", data={})
        self.assertEqual(response.status_code, 400)  # Should be 400 due to validation
        self.assertIn(b"Missing or invalid URL", response.data)
