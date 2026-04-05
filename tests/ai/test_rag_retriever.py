import pytest
from unittest.mock import patch, MagicMock
from app.ai.rag_retriever import (
    retrieve_destination_info,
    retrieve_place_context,
    build_rag_query,
    PREFERENCE_QUERY_MAP,
)


class TestBuildRagQuery:
    def test_basic_query(self):
        result = build_rag_query("Tokyo", "best food", None)
        assert "Tokyo" in result
        assert "best food" in result
        assert "travel guide" in result

    def test_with_preferences(self):
        result = build_rag_query("Tokyo", "trip", ["Food", "Nature"])
        assert "local food street food restaurants" in result
        assert "nature parks and outdoor activities" in result

    def test_limits_to_3_preferences(self):
        prefs = ["Food", "Nature", "Museum", "History", "Shopping"]
        result = build_rag_query("Tokyo", "trip", prefs)
        # Only first 3 should be included
        assert PREFERENCE_QUERY_MAP["Food"] in result
        assert PREFERENCE_QUERY_MAP["Nature"] in result
        assert PREFERENCE_QUERY_MAP["Museum"] in result
        assert PREFERENCE_QUERY_MAP["History"] not in result

    def test_unknown_preference_used_as_is(self):
        result = build_rag_query("Tokyo", "trip", ["CustomPref"])
        assert "CustomPref" in result

    def test_no_preferences(self):
        result = build_rag_query("Tokyo", "trip", [])
        assert result == "Tokyo  trip travel guide"


class TestRetrievePlaceContext:
    @patch("app.ai.rag_retriever.retrieve_destination_info")
    def test_calls_with_first_destination(self, mock_retrieve):
        mock_retrieve.return_value = "info about Tokyo"
        result = retrieve_place_context(["Tokyo", "Osaka"], "best food")
        mock_retrieve.assert_called_once_with("Tokyo", "best food")
        assert result == "info about Tokyo"

    def test_empty_destinations_returns_empty(self):
        result = retrieve_place_context([], "query")
        assert result == ""


class TestRetrieveDestinationInfo:
    @patch("app.ai.rag_retriever._get_tavily")
    def test_returns_formatted_results(self, mock_get_tavily):
        mock_client = MagicMock()
        mock_get_tavily.return_value = mock_client
        mock_client.search.return_value = {
            "answer": "Tokyo is great",
            "results": [
                {"title": "Guide", "content": "Tokyo travel guide content"},
            ],
        }
        result = retrieve_destination_info("Tokyo", "food")
        assert "Tokyo is great" in result
        assert "Guide" in result

    @patch("app.ai.rag_retriever._get_tavily")
    def test_no_results_returns_fallback(self, mock_get_tavily):
        mock_client = MagicMock()
        mock_get_tavily.return_value = mock_client
        mock_client.search.return_value = {"answer": "", "results": []}
        result = retrieve_destination_info("Unknown", "query")
        assert result == "No live information retrieved"
