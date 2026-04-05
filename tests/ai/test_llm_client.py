import pytest
from unittest.mock import patch
from app.ai.llm_client import get_llm_client, _PROVIDER_CONFIG


class TestGetLlmClient:
    def setup_method(self):
        # Clear lru_cache between tests
        get_llm_client.cache_clear()

    @patch("app.ai.llm_client.settings")
    @patch("app.ai.llm_client.OpenAI")
    def test_returns_openai_client(self, mock_openai_cls, mock_settings):
        mock_settings.LLM_PROVIDER = "openrouter"
        mock_settings.OPENROUTER_API_KEY = "test-key"
        # Re-patch _PROVIDER_CONFIG since it was evaluated at import time
        with patch.dict(
            "app.ai.llm_client._PROVIDER_CONFIG",
            {"openrouter": ("https://openrouter.ai/api/v1", "test-key")},
        ):
            get_llm_client()
            mock_openai_cls.assert_called_once_with(
                base_url="https://openrouter.ai/api/v1", api_key="test-key"
            )

    @patch("app.ai.llm_client.settings")
    def test_unsupported_provider_raises(self, mock_settings):
        mock_settings.LLM_PROVIDER = "nonexistent"
        with patch.dict("app.ai.llm_client._PROVIDER_CONFIG", {}, clear=True):
            with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
                get_llm_client()

    def test_provider_config_has_expected_providers(self):
        expected = {"openrouter", "gemini", "groq", "openai", "ollama"}
        assert set(_PROVIDER_CONFIG.keys()) == expected
