import pytest
import json
from unittest.mock import MagicMock, patch
from app.services.ai_service import (
    _normalize_destinations,
    _extract_destinations_via_json,
    _save_draft_to_redis,
    plan_trip_ai,
    suggest_next_destination,
)


class TestNormalizeDestinations:
    def test_basic_normalization(self):
        raw = [
            {"name": "Tokyo Tower", "visit_date": "2025-01-01", "order_index": 99},
            {"name": "Senso-ji", "visit_date": None, "order_index": 5},
        ]
        result = _normalize_destinations(raw)
        assert len(result) == 2
        # order_index should be re-indexed
        assert result[0]["order_index"] == 0
        assert result[1]["order_index"] == 1
        assert result[0]["name"] == "Tokyo Tower"

    def test_skips_non_dict(self):
        result = _normalize_destinations(["not a dict", 42, None])
        assert result == []

    def test_skips_missing_name(self):
        result = _normalize_destinations([{"visit_date": "2025-01-01"}])
        assert result == []

    def test_skips_empty_name(self):
        result = _normalize_destinations([{"name": ""}, {"name": "   "}])
        assert result == []

    def test_strips_name_whitespace(self):
        result = _normalize_destinations([{"name": "  Tokyo  "}])
        assert result[0]["name"] == "Tokyo"

    def test_preserves_optional_fields(self):
        raw = [{"name": "Place", "visit_date": "2025-01-01", "visit_start_time": "09:00", "visit_end_time": "17:00"}]
        result = _normalize_destinations(raw)
        assert result[0]["visit_date"] == "2025-01-01"
        assert result[0]["visit_start_time"] == "09:00"
        assert result[0]["visit_end_time"] == "17:00"

    def test_empty_list(self):
        assert _normalize_destinations([]) == []


class TestExtractDestinationsViaJson:
    def _make_client(self, content: str):
        client = MagicMock()
        message = MagicMock()
        message.content = content
        choice = MagicMock()
        choice.message = message
        response = MagicMock()
        response.choices = [choice]
        client.chat.completions.create.return_value = response
        return client

    def test_clean_json(self):
        data = json.dumps({"destinations": [{"name": "Tokyo Tower", "order_index": 0}]})
        client = self._make_client(data)
        result = _extract_destinations_via_json(client, "itinerary text")
        assert len(result) == 1
        assert result[0]["name"] == "Tokyo Tower"

    def test_markdown_wrapped_json(self):
        data = '```json\n{"destinations": [{"name": "Senso-ji", "order_index": 0}]}\n```'
        client = self._make_client(data)
        result = _extract_destinations_via_json(client, "text")
        assert len(result) == 1
        assert result[0]["name"] == "Senso-ji"

    def test_json_with_extra_text(self):
        data = 'Here are the destinations:\n{"destinations": [{"name": "Fushimi Inari", "order_index": 0}]}\nDone!'
        client = self._make_client(data)
        result = _extract_destinations_via_json(client, "text")
        assert len(result) == 1

    def test_empty_response(self):
        client = self._make_client("")
        result = _extract_destinations_via_json(client, "text")
        assert result == []

    def test_invalid_json(self):
        client = self._make_client("this is not json at all")
        result = _extract_destinations_via_json(client, "text")
        assert result == []


class TestSaveDraftToRedis:
    @patch("app.services.ai_service.get_redis")
    def test_saves_and_returns_draft_id(self, mock_get_redis):
        redis_mock = MagicMock()
        mock_get_redis.return_value = redis_mock

        destinations = [{"name": "Tokyo", "order_index": 0}]
        draft_id = _save_draft_to_redis("user-1", destinations)

        assert draft_id is not None
        redis_mock.setex.assert_called_once()
        key = redis_mock.setex.call_args[0][0]
        assert key.startswith("trip_draft:user-1:")

    @patch("app.services.ai_service.get_redis")
    def test_empty_destinations_returns_none(self, mock_get_redis):
        result = _save_draft_to_redis("user-1", [])
        assert result is None

    @patch("app.services.ai_service.get_redis")
    def test_invalid_destinations_returns_none(self, mock_get_redis):
        result = _save_draft_to_redis("user-1", [{"no_name": True}])
        assert result is None

    @patch("app.services.ai_service.get_redis")
    def test_no_redis_returns_none(self, mock_get_redis):
        mock_get_redis.return_value = None
        result = _save_draft_to_redis("user-1", [{"name": "X", "order_index": 0}])
        assert result is None


class TestPlanTripAi:
    @patch("app.services.ai_service._save_draft_to_redis")
    @patch("app.services.ai_service.get_llm_client")
    @patch("app.services.ai_service.build_user_message")
    @patch("app.services.ai_service.build_system_prompt")
    @patch("app.services.ai_service.build_user_context")
    def test_non_thinking_path_with_tool_calls(
        self, mock_ctx, mock_sys, mock_msg, mock_client, mock_draft
    ):
        mock_ctx.return_value = {"user": {"name": "T"}, "past_trips": [], "visited_places": []}
        mock_sys.return_value = "system prompt"
        mock_msg.return_value = "user message"

        tool_call = MagicMock()
        tool_call.function.arguments = json.dumps({
            "destinations": [{"name": "Tokyo", "order_index": 0}]
        })
        message = MagicMock()
        message.content = "Here is your plan"
        message.tool_calls = [tool_call]
        choice = MagicMock()
        choice.message = message
        response = MagicMock()
        response.choices = [choice]
        client = MagicMock()
        client.chat.completions.create.return_value = response
        mock_client.return_value = client
        mock_draft.return_value = "draft-123"

        with patch("app.services.ai_service.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "openrouter"
            mock_settings.LLM_MODEL = "test-model"
            mock_settings.TAVILY_API_KEY = ""
            result = plan_trip_ai("user-1", "3 day trip to Tokyo")

        assert result["result"] == "Here is your plan"
        assert result["draft_id"] == "draft-123"
        assert result["thinking"] is None

    @patch("app.services.ai_service._save_draft_to_redis")
    @patch("app.services.ai_service._extract_destinations_via_json")
    @patch("app.ai.gemini_native.generate_content_with_thinking")
    @patch("app.services.ai_service.get_llm_client")
    @patch("app.services.ai_service.build_user_message")
    @patch("app.services.ai_service.build_system_prompt")
    @patch("app.services.ai_service.build_user_context")
    def test_gemini_thinking_path(
        self, mock_ctx, mock_sys, mock_msg, mock_client, mock_gemini, mock_extract, mock_draft
    ):
        mock_ctx.return_value = {"user": {"name": "T"}, "past_trips": [], "visited_places": []}
        mock_sys.return_value = "system prompt"
        mock_msg.return_value = "user message"
        mock_client.return_value = MagicMock()

        mock_gemini.return_value = {
            "content": "Itinerary here",
            "thinking": "Let me think...",
        }
        mock_extract.return_value = [{"name": "Tokyo", "order_index": 0}]
        mock_draft.return_value = "draft-456"

        with patch("app.services.ai_service.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "gemini"
            mock_settings.LLM_MODEL = "google/gemini-2.0-flash"
            mock_settings.TAVILY_API_KEY = ""
            result = plan_trip_ai("user-1", "plan trip", thinking_process_toggle=True)

        assert result["result"] == "Itinerary here"
        assert result["thinking"] == "Let me think..."
        assert result["draft_id"] == "draft-456"


class TestSuggestNextDestination:
    @patch("app.services.ai_service.get_llm_client")
    @patch("app.services.ai_service.build_system_prompt")
    @patch("app.services.ai_service.build_user_context")
    def test_returns_suggestion(self, mock_ctx, mock_sys, mock_client):
        mock_ctx.return_value = {"user": {"name": "T"}, "past_trips": [], "visited_places": []}
        mock_sys.return_value = "prompt"

        message = MagicMock()
        message.content = "Try visiting Osaka"
        choice = MagicMock()
        choice.message = message
        response = MagicMock()
        response.choices = [choice]
        client = MagicMock()
        client.chat.completions.create.return_value = response
        mock_client.return_value = client

        with patch("app.services.ai_service.settings") as mock_settings:
            mock_settings.LLM_MODEL = "test-model"
            result = suggest_next_destination("user-1", "Japan")

        assert result == "Try visiting Osaka"
