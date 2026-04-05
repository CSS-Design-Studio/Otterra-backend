import pytest
from app.ai.prompt_templates import build_system_prompt, build_user_message


@pytest.fixture
def sample_cag_context():
    return {
        "user": {"name": "TestUser"},
        "visited_places": ["Tokyo Tower", "Kyoto Temple"],
        "past_trips": [
            {
                "title": "Japan Trip",
                "status": "completed",
                "destinations": ["Tokyo Tower", "Kyoto Temple"],
                "budget": "5000 USD",
            }
        ],
    }


@pytest.fixture
def empty_cag_context():
    return {
        "user": {"name": "NewUser"},
        "visited_places": [],
        "past_trips": [],
    }


class TestBuildSystemPrompt:
    def test_includes_user_name(self, sample_cag_context):
        prompt = build_system_prompt(sample_cag_context)
        assert "TestUser" in prompt

    def test_includes_visited_places(self, sample_cag_context):
        prompt = build_system_prompt(sample_cag_context)
        assert "Tokyo Tower" in prompt
        assert "Kyoto Temple" in prompt

    def test_includes_past_trips(self, sample_cag_context):
        prompt = build_system_prompt(sample_cag_context)
        assert "Japan Trip" in prompt
        assert "5000 USD" in prompt

    def test_empty_visited_shows_none_yet(self, empty_cag_context):
        prompt = build_system_prompt(empty_cag_context)
        assert "none yet" in prompt

    def test_no_itinerary_flag_by_default(self, sample_cag_context):
        prompt = build_system_prompt(sample_cag_context)
        assert "<has_itinerary>" not in prompt

    def test_includes_itinerary_flag_when_toggled(self, sample_cag_context):
        prompt = build_system_prompt(sample_cag_context, include_itinerary_flag=True)
        assert "<has_itinerary>true</has_itinerary>" in prompt
        assert "<has_itinerary>false</has_itinerary>" in prompt

    def test_caps_past_trips_at_5(self):
        ctx = {
            "user": {"name": "User"},
            "visited_places": [],
            "past_trips": [
                {"title": f"Trip {i}", "status": "completed", "destinations": [], "budget": "100 USD"}
                for i in range(10)
            ],
        }
        prompt = build_system_prompt(ctx)
        # Only first 5 should appear
        assert "Trip 0" in prompt
        assert "Trip 4" in prompt
        assert "Trip 5" not in prompt


class TestBuildUserMessage:
    def test_without_rag_returns_query(self):
        msg = build_user_message("Plan a trip to Tokyo")
        assert msg == "Plan a trip to Tokyo"

    def test_with_rag_includes_search_results(self):
        msg = build_user_message("Plan a trip to Tokyo", "Some live info about Tokyo")
        assert "## Live Search Results" in msg
        assert "Some live info about Tokyo" in msg
        assert "## User Question" in msg
        assert "Plan a trip to Tokyo" in msg

    def test_empty_rag_returns_query_only(self):
        msg = build_user_message("My query", "")
        assert msg == "My query"
