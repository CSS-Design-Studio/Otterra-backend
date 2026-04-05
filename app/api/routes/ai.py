from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse 
from app.core.security import get_current_token
from app.core.rate_limit import rate_limit_ai_chat
from app.services.ai_service import plan_trip_ai, suggest_next_destination, chat_ai
from app.schemas_DTO.ai import TripPlanRequest, AISuggestionResponse, ChatRequest
from app.core.config import settings

router = APIRouter()

@router.post("/plan", response_model = AISuggestionResponse)
def plan_trip(
    body: TripPlanRequest,
    payload: dict = Depends(get_current_token),
):
    """
    CAG + RAG: personalised trip planning with optional live destination info
    """
    user_id = payload.get("sub")
    try:
        result = plan_trip_ai(
            user_id = user_id,
            user_query = body.query,
            trip_destinations = body.destinations,
            use_web_search = body.use_web_search,
            preferences=body.preferences,
            thinking_process_toggle = body.thinking_process_toggle,
            trip_days=body.trip_days,
        )
        return AISuggestionResponse(result=result["result"], 
                                    provider=settings.LLM_PROVIDER,
                                    thinking_process=result["thinking"],
                                    draft_id=result.get("draft_id"),
                                    )
    except Exception as e:
        raise HTTPException(status_code = 500, detail=str(e))

@router.get("/suggest/{country}", response_model = AISuggestionResponse)
def suggest_destinations(
    country: str,
    payload: dict = Depends(get_current_token),
):
    """
    CAG-only: get the suggestion of next destination for user based on user's travel history
    """
    user_id = payload.get("sub")
    try:
        result = suggest_next_destination(user_id, country)
        return AISuggestionResponse(result=result, provider=settings.LLM_PROVIDER)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
def chat(
    body: ChatRequest,
    payload: dict = Depends(get_current_token),
    _: None = Depends(rate_limit_ai_chat)
):
    """
    Streaming chat with CAG + RAG and conversation history
    """

    user_id = payload.get("sub")
    generator = chat_ai(
        user_id=user_id,
        message=body.message,
        conversation_id=body.conversation_id,
        destinations=body.destinations,
        use_web_search=body.use_web_search,
        thinking_process_toggle=body.thinking_process_toggle,
    )
    return StreamingResponse(generator, media_type="text/event-stream")
        

