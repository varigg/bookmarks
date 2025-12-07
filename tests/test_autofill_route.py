import unittest
from unittest.mock import patch, MagicMock
from bookmarks import create_app


class TestAutofillRoute(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.app.config["TESTING"] = True

    @patch("bookmarks.routes.PerplexityClientFactory")
    def test_autofill_success(self, mock_factory):
        # Mock the client and its response
        mock_client = MagicMock()
        mock_client.generate_description.return_value = {
            "title": "Test Title",
            "description": "Test Description",
        }
        mock_factory.create_client.return_value = mock_client

        # Make request
        response = self.client.post(
            "/bookmarks/autofill", data={"url": "https://example.com"}
        )

        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'value="https://example.com"', response.data)
        self.assertIn(b'value="Test Title"', response.data)
        self.assertIn(b"Test Description", response.data)

        # Verify client was called
        mock_factory.create_client.assert_called_once()
        mock_client.generate_description.assert_called_once_with("https://example.com")

    @patch("bookmarks.routes.PerplexityClientFactory")
    def test_autofill_error(self, mock_factory):
        # Mock error
        mock_factory.create_client.side_effect = Exception("API Error")

        # Make request
        response = self.client.post(
            "/bookmarks/autofill", data={"url": "https://example.com"}
        )

        # Verify response (should still render page but with error message)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Error generating description", response.data)
        self.assertIn(b'value="https://example.com"', response.data)

    def test_autofill_no_url(self):
        response = self.client.post("/bookmarks/autofill", data={})
        self.assertEqual(response.status_code, 302)  # Redirects back
