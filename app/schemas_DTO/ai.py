from pydantic import BaseModel
from typing import Optional

class TripPlanRequest(BaseModel):
    query: str                                     # e.g. "3-day itinerary in Osaka"
    destinations: Optional[list[str]] = None       # e.g. ["Osaka", "Kyoto"]
    use_web_search: bool = True                    # False = CAG only, skip Tavily
    preferences: Optional[list[str]] = None
    thinking_process_toggle: bool = False
    trip_days: Optional[int] = None

class AISuggestionResponse(BaseModel):
    result: str
    provider: str
    thinking_process: Optional[str] = None
    draft_id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    destinations: Optional[list[str]] = None
    use_web_search: bool = True
    thinking_process_toggle: bool = False

class SaveAiDraftRequest(BaseModel):
    trip_id: str
    draft_id: str
    selected_indexes: list[int]
