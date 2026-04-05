import pytest
import json
from unittest.mock import MagicMock, patch
from app.services.trip_service import TripService


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def svc(mock_repo):
    return TripService(trip_repository=mock_repo)


@pytest.fixture
def sample_trip():
    return {
        "id": "trip-1",
        "title": "Japan Trip",
        "owner_id": "user-1",
        "status": "planning",
        "is_public": False,
        "start_date": "2025-01-01",
        "end_date": "2025-01-07",
    }


class TestCreateTrip:
    def test_success(self, svc, mock_repo):
        mock_repo.create.return_value = {"id": "trip-1", "title": "My Trip", "owner_id": "user-1"}
        result = svc.create_trip({"title": "My Trip"}, "user-1")
        assert result["title"] == "My Trip"
        assert result["owner_id"] == "user-1"

    def test_empty_title_raises(self, svc):
        with pytest.raises(ValueError, match="旅程標題不能為空"):
            svc.create_trip({"title": ""}, "user-1")

    def test_no_title_raises(self, svc):
        with pytest.raises(ValueError):
            svc.create_trip({}, "user-1")

    def test_end_date_before_start_raises(self, svc):
        with pytest.raises(ValueError, match="結束日期不能早於開始日期"):
            svc.create_trip({
                "title": "Trip",
                "start_date": "2025-01-10",
                "end_date": "2025-01-05",
            }, "user-1")

    def test_default_status_is_planning(self, svc, mock_repo):
        mock_repo.create.return_value = {"id": "t1", "title": "T", "owner_id": "u1", "status": "planning"}
        svc.create_trip({"title": "T"}, "u1")
        call_data = mock_repo.create.call_args[0][0]
        assert call_data["status"] == "planning"

    def test_default_is_public_false(self, svc, mock_repo):
        mock_repo.create.return_value = {"id": "t1", "title": "T", "owner_id": "u1"}
        svc.create_trip({"title": "T"}, "u1")
        call_data = mock_repo.create.call_args[0][0]
        assert call_data["is_public"] is False

    def test_with_destinations(self, svc, mock_repo):
        mock_repo.create.return_value = {"id": "trip-1", "title": "Trip"}
        mock_repo.create_destination.return_value = {"id": "dest-1", "name": "Tokyo"}

        result = svc.create_trip({
            "title": "Trip",
            "destinations": [{"name": "Tokyo"}],
        }, "user-1")

        mock_repo.create_destination.assert_called_once()
        assert "destinations" in result


class TestGetTripById:
    def test_found_as_owner(self, svc, mock_repo, sample_trip):
        mock_repo.find_by_id.return_value = sample_trip.copy()
        result = svc.get_trip_by_id("trip-1", "user-1")
        assert result is not None
        assert result["id"] == "trip-1"

    def test_not_found(self, svc, mock_repo):
        mock_repo.find_by_id.return_value = None
        result = svc.get_trip_by_id("nonexistent", "user-1")
        assert result is None

    def test_not_owner_private_trip_returns_none(self, svc, mock_repo, sample_trip):
        mock_repo.find_by_id.return_value = sample_trip.copy()
        result = svc.get_trip_by_id("trip-1", "other-user")
        assert result is None

    def test_not_owner_public_trip_returns_trip(self, svc, mock_repo, sample_trip):
        trip = sample_trip.copy()
        trip["is_public"] = True
        mock_repo.find_by_id.return_value = trip
        result = svc.get_trip_by_id("trip-1", "other-user")
        assert result is not None


class TestGetMyTrips:
    def test_returns_paginated_result(self, svc, mock_repo):
        mock_repo.find_by_owner.return_value = [{"id": "t1"}, {"id": "t2"}]
        mock_repo.count_by_owner.return_value = 2

        result = svc.get_my_trips("user-1", page=1, page_size=10)
        assert result["total"] == 2
        assert result["page"] == 1
        assert result["page_size"] == 10
        assert len(result["trips"]) == 2

    def test_passes_status_filter(self, svc, mock_repo):
        mock_repo.find_by_owner.return_value = []
        mock_repo.count_by_owner.return_value = 0
        svc.get_my_trips("user-1", status="completed")
        mock_repo.find_by_owner.assert_called_once_with(
            owner_id="user-1", page=1, page_size=10, status="completed", include_destinations=False
        )


class TestUpdateTrip:
    def test_success(self, svc, mock_repo, sample_trip):
        mock_repo.find_by_id.return_value = sample_trip.copy()
        mock_repo.update.return_value = {**sample_trip, "title": "Updated"}
        mock_repo.get_destinations_by_trip_id.return_value = []

        result = svc.update_trip("trip-1", {"title": "Updated"}, "user-1")
        assert result["title"] == "Updated"

    def test_not_found_returns_none(self, svc, mock_repo):
        mock_repo.find_by_id.return_value = None
        result = svc.update_trip("nonexistent", {"title": "X"}, "user-1")
        assert result is None

    def test_not_owner_raises_permission_error(self, svc, mock_repo, sample_trip):
        mock_repo.find_by_id.return_value = sample_trip.copy()
        with pytest.raises(PermissionError):
            svc.update_trip("trip-1", {"title": "X"}, "other-user")

    def test_invalid_dates_raises(self, svc, mock_repo, sample_trip):
        mock_repo.find_by_id.return_value = sample_trip.copy()
        with pytest.raises(ValueError, match="結束日期不能早於開始日期"):
            svc.update_trip("trip-1", {
                "start_date": "2025-12-01",
                "end_date": "2025-01-01",
            }, "user-1")


class TestUpdateTripStatus:
    def test_success(self, svc, mock_repo, sample_trip):
        mock_repo.find_by_id.return_value = sample_trip.copy()
        mock_repo.update_status.return_value = {**sample_trip, "status": "ongoing"}
        result = svc.update_trip_status("trip-1", "ongoing", "user-1")
        assert result is not None

    def test_invalid_status_raises(self, svc):
        with pytest.raises(ValueError, match="Invalid status"):
            svc.update_trip_status("trip-1", "invalid", "user-1")

    def test_trip_not_found_returns_none(self, svc, mock_repo):
        mock_repo.find_by_id.return_value = None
        result = svc.update_trip_status("nonexistent", "ongoing", "user-1")
        assert result is None


class TestDeleteTrip:
    def test_success(self, svc, mock_repo, sample_trip):
        mock_repo.find_by_id.return_value = sample_trip.copy()
        mock_repo.delete.return_value = True
        assert svc.delete_trip("trip-1", "user-1") is True

    def test_not_found(self, svc, mock_repo):
        mock_repo.find_by_id.return_value = None
        assert svc.delete_trip("nonexistent", "user-1") is False

    def test_not_owner_raises(self, svc, mock_repo, sample_trip):
        mock_repo.find_by_id.return_value = sample_trip.copy()
        with pytest.raises(PermissionError):
            svc.delete_trip("trip-1", "other-user")


class TestAddDestination:
    def test_success(self, svc, mock_repo, sample_trip):
        mock_repo.find_by_id.return_value = sample_trip.copy()
        mock_repo.get_destinations_by_trip_id.return_value = []
        mock_repo.create_destination.return_value = {"id": "d1", "name": "Tokyo"}

        result = svc.add_destination("trip-1", {"name": "Tokyo"}, "user-1")
        assert result["name"] == "Tokyo"

    def test_trip_not_found_raises(self, svc, mock_repo):
        mock_repo.find_by_id.return_value = None
        with pytest.raises(ValueError, match="旅程不存在"):
            svc.add_destination("nonexistent", {"name": "X"}, "user-1")

    def test_not_owner_raises(self, svc, mock_repo, sample_trip):
        mock_repo.find_by_id.return_value = sample_trip.copy()
        with pytest.raises(PermissionError):
            svc.add_destination("trip-1", {"name": "X"}, "other-user")

    def test_auto_order_index(self, svc, mock_repo, sample_trip):
        mock_repo.find_by_id.return_value = sample_trip.copy()
        mock_repo.get_destinations_by_trip_id.return_value = [{"id": "d1"}, {"id": "d2"}]
        mock_repo.create_destination.return_value = {"id": "d3", "name": "New", "order_index": 2}

        svc.add_destination("trip-1", {"name": "New"}, "user-1")
        call_data = mock_repo.create_destination.call_args[0][0]
        assert call_data["order_index"] == 2


class TestUpdateDestination:
    def test_success(self, svc, mock_repo, sample_trip):
        mock_repo.find_destination_by_id.return_value = {"id": "d1", "trip_id": "trip-1"}
        mock_repo.find_by_id.return_value = sample_trip.copy()
        mock_repo.update_destination.return_value = {"id": "d1", "name": "Updated"}

        result = svc.update_destination("d1", {"name": "Updated"}, "user-1")
        assert result["name"] == "Updated"

    def test_not_found(self, svc, mock_repo):
        mock_repo.find_destination_by_id.return_value = None
        result = svc.update_destination("nonexistent", {"name": "X"}, "user-1")
        assert result is None

    def test_not_owner_raises(self, svc, mock_repo, sample_trip):
        mock_repo.find_destination_by_id.return_value = {"id": "d1", "trip_id": "trip-1"}
        mock_repo.find_by_id.return_value = sample_trip.copy()
        with pytest.raises(PermissionError):
            svc.update_destination("d1", {"name": "X"}, "other-user")


class TestDeleteDestination:
    def test_success(self, svc, mock_repo, sample_trip):
        mock_repo.find_destination_by_id.return_value = {"id": "d1", "trip_id": "trip-1"}
        mock_repo.find_by_id.return_value = sample_trip.copy()
        mock_repo.delete_destination.return_value = True
        assert svc.delete_destination("d1", "user-1") is True

    def test_not_found(self, svc, mock_repo):
        mock_repo.find_destination_by_id.return_value = None
        assert svc.delete_destination("nonexistent", "user-1") is False

    def test_not_owner_raises(self, svc, mock_repo, sample_trip):
        mock_repo.find_destination_by_id.return_value = {"id": "d1", "trip_id": "trip-1"}
        mock_repo.find_by_id.return_value = sample_trip.copy()
        with pytest.raises(PermissionError):
            svc.delete_destination("d1", "other-user")


class TestGetPublicTrips:
    def test_returns_paginated(self, svc, mock_repo):
        mock_repo.find_public_trips.return_value = [{"id": "t1", "is_public": True}]
        mock_repo.count_public_trips.return_value = 1

        result = svc.get_public_trips(page=1, page_size=10, keyword="japan")
        assert result["total"] == 1
        assert len(result["trips"]) == 1


class TestSaveAiDestinationsToTrip:
    @patch("app.services.trip_service.get_redis")
    def test_success(self, mock_get_redis, svc, mock_repo, sample_trip):
        redis_mock = MagicMock()
        mock_get_redis.return_value = redis_mock

        destinations = [
            {"name": "Tokyo Tower", "order_index": 0, "visit_date": "2025-01-01"},
            {"name": "Senso-ji", "order_index": 1, "visit_date": "2025-01-02"},
            {"name": "Shibuya", "order_index": 2, "visit_date": "2025-01-03"},
        ]
        redis_mock.get.return_value = json.dumps(destinations)
        mock_repo.find_by_id.return_value = sample_trip.copy()

        result = svc.save_ai_destinations_to_trip("user-1", "trip-1", "draft-1", [0, 2])
        assert result is True
        assert mock_repo.create_destination.call_count == 2
        redis_mock.delete.assert_called_once()

    @patch("app.services.trip_service.get_redis")
    def test_no_redis_returns_false(self, mock_get_redis, svc):
        mock_get_redis.return_value = None
        result = svc.save_ai_destinations_to_trip("user-1", "trip-1", "draft-1", [0])
        assert result is False

    @patch("app.services.trip_service.get_redis")
    def test_draft_not_found_returns_false(self, mock_get_redis, svc):
        redis_mock = MagicMock()
        redis_mock.get.return_value = None
        mock_get_redis.return_value = redis_mock
        result = svc.save_ai_destinations_to_trip("user-1", "trip-1", "draft-1", [0])
        assert result is False

    @patch("app.services.trip_service.get_redis")
    def test_not_owner_returns_false(self, mock_get_redis, svc, mock_repo, sample_trip):
        redis_mock = MagicMock()
        redis_mock.get.return_value = json.dumps([{"name": "X", "order_index": 0}])
        mock_get_redis.return_value = redis_mock
        mock_repo.find_by_id.return_value = sample_trip.copy()  # owner_id = "user-1"

        result = svc.save_ai_destinations_to_trip("other-user", "trip-1", "draft-1", [0])
        assert result is False
