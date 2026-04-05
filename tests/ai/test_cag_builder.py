import pytest
import json
from unittest.mock import patch, MagicMock
from app.ai.cag_builder import build_user_context, invalidate_user_context, CAG_TTL


@pytest.fixture
def mock_supabase_data():
    """Supabase response fixtures"""
    user_resp = MagicMock()
    user_resp.data = {"username": "traveler1", "first_name": "John", "last_name": "Doe"}

    trip_resp = MagicMock()
    trip_resp.data = [
        {
            "title": "Japan Trip",
            "description": "Exploring Japan",
            "start_date": "2024-01-01",
            "end_date": "2024-01-07",
            "status": "completed",
            "budget_amount": 5000,
            "budget_currency": "USD",
            "trip_destinations": [
                {"name": "Tokyo Tower", "description": "", "address": "", "latitude": 0, "longitude": 0, "notes": ""},
            ],
        },
        {
            "title": "Planning Trip",
            "description": "",
            "start_date": "2025-06-01",
            "end_date": "2025-06-05",
            "status": "planning",
            "budget_amount": 3000,
            "budget_currency": "EUR",
            "trip_destinations": [
                {"name": "Eiffel Tower", "description": "", "address": "", "latitude": 0, "longitude": 0, "notes": ""},
            ],
        },
    ]
    return user_resp, trip_resp


class TestBuildUserContext:
    @patch("app.ai.cag_builder.get_supabase")
    @patch("app.ai.cag_builder.get_redis")
    def test_returns_from_redis_cache(self, mock_get_redis, mock_get_supabase):
        cached_data = {"user": {"name": "cached"}, "past_trips": [], "visited_places": []}
        redis_mock = MagicMock()
        redis_mock.get.return_value = json.dumps(cached_data)
        mock_get_redis.return_value = redis_mock

        result = build_user_context("user-1")
        assert result == cached_data
        mock_get_supabase.assert_not_called()

    @patch("app.ai.cag_builder.get_supabase")
    @patch("app.ai.cag_builder.get_redis")
    def test_falls_back_to_supabase(self, mock_get_redis, mock_get_supabase, mock_supabase_data):
        redis_mock = MagicMock()
        redis_mock.get.return_value = None
        mock_get_redis.return_value = redis_mock

        user_resp, trip_resp = mock_supabase_data
        supabase_mock = MagicMock()
        supabase_mock.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
        supabase_mock.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = trip_resp
        mock_get_supabase.return_value = supabase_mock

        result = build_user_context("user-1")
        assert result["user"]["name"] == "traveler1"
        assert len(result["past_trips"]) == 2
        # Only completed trip destinations count as visited
        assert "Tokyo Tower" in result["visited_places"]
        assert "Eiffel Tower" not in result["visited_places"]

    @patch("app.ai.cag_builder.get_supabase")
    @patch("app.ai.cag_builder.get_redis")
    def test_caches_to_redis(self, mock_get_redis, mock_get_supabase, mock_supabase_data):
        redis_mock = MagicMock()
        redis_mock.get.return_value = None
        mock_get_redis.return_value = redis_mock

        user_resp, trip_resp = mock_supabase_data
        supabase_mock = MagicMock()
        supabase_mock.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
        supabase_mock.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = trip_resp
        mock_get_supabase.return_value = supabase_mock

        build_user_context("user-1")
        redis_mock.setex.assert_called_once()
        args = redis_mock.setex.call_args
        assert args[0][0] == "cag:user:user-1"
        assert args[0][1] == CAG_TTL

    @patch("app.ai.cag_builder.get_supabase")
    @patch("app.ai.cag_builder.get_redis")
    def test_works_without_redis(self, mock_get_redis, mock_get_supabase, mock_supabase_data):
        mock_get_redis.return_value = None

        user_resp, trip_resp = mock_supabase_data
        supabase_mock = MagicMock()
        supabase_mock.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
        supabase_mock.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = trip_resp
        mock_get_supabase.return_value = supabase_mock

        result = build_user_context("user-1")
        assert result["user"]["name"] == "traveler1"


class TestInvalidateUserContext:
    @patch("app.ai.cag_builder.get_redis")
    def test_deletes_cache_key(self, mock_get_redis):
        redis_mock = MagicMock()
        mock_get_redis.return_value = redis_mock
        invalidate_user_context("user-1")
        redis_mock.delete.assert_called_once_with("cag:user:user-1")

    @patch("app.ai.cag_builder.get_redis")
    def test_no_error_without_redis(self, mock_get_redis):
        mock_get_redis.return_value = None
        invalidate_user_context("user-1")  # Should not raise
