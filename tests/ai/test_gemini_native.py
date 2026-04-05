import pytest
from unittest.mock import patch, MagicMock
from app.ai.gemini_native import _normalize_model, generate_content_with_thinking


class TestNormalizeModel:
    def test_strips_google_prefix(self):
        assert _normalize_model("google/gemini-2.0-flash") == "gemini-2.0-flash"

    def test_keeps_model_without_prefix(self):
        assert _normalize_model("gemini-2.0-flash") == "gemini-2.0-flash"

    def test_other_prefix_unchanged(self):
        assert _normalize_model("openai/gpt-4") == "openai/gpt-4"


class TestGenerateContentWithThinking:
    @patch("app.ai.gemini_native.settings")
    @patch("app.ai.gemini_native.genai")
    def test_returns_content_and_thinking(self, mock_genai, mock_settings):
        mock_settings.GEMINI_API_KEY = "test-key"
        mock_settings.GEMINI_THINKING_BUDGET = -1

        # Build mock response
        thinking_part = MagicMock()
        thinking_part.text = "I should plan for Tokyo"
        thinking_part.thought = True

        answer_part = MagicMock()
        answer_part.text = "Here is your itinerary"
        answer_part.thought = False

        candidate = MagicMock()
        candidate.content.parts = [thinking_part, answer_part]

        mock_response = MagicMock()
        mock_response.candidates = [candidate]

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        result = generate_content_with_thinking(
            system_prompt="You are a travel assistant",
            user_message="Plan a trip to Tokyo",
            model="google/gemini-2.0-flash",
            max_output_tokens=4096,
        )

        assert result["content"] == "Here is your itinerary"
        assert result["thinking"] == "I should plan for Tokyo"

    @patch("app.ai.gemini_native.settings")
    @patch("app.ai.gemini_native.genai")
    def test_no_thinking_returns_none(self, mock_genai, mock_settings):
        mock_settings.GEMINI_API_KEY = "test-key"
        mock_settings.GEMINI_THINKING_BUDGET = -1

        answer_part = MagicMock()
        answer_part.text = "Answer only"
        answer_part.thought = False

        candidate = MagicMock()
        candidate.content.parts = [answer_part]

        mock_response = MagicMock()
        mock_response.candidates = [candidate]

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        result = generate_content_with_thinking(
            system_prompt="sys",
            user_message="msg",
            model="gemini-2.0-flash",
            max_output_tokens=4096,
        )

        assert result["content"] == "Answer only"
        assert result["thinking"] is None
