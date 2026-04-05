from app.ai.llm_client import get_llm_client
from app.ai.cag_builder import build_user_context
from app.ai.rag_retriever import retrieve_place_context, build_rag_query
from app.ai.prompt_templates import build_system_prompt, build_user_message
from app.core.config import settings
from app.db.redis import get_redis
import re
import json
import uuid
from typing import Generator

# ============================================================================
# Function calling tool definition for structured destination extraction
# Placed at module level so it can be reused across functions
# ============================================================================
DESTINATION_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "save_destinations",
            "description": "Extract structured destinations from the itinerary",
            "parameters": {
                "type": "object",
                "properties": {
                    "destinations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "visit_date": {"type": "string"},
                                "visit_start_time": {"type": "string"},
                                "visit_end_time": {"type": "string"},
                                "order_index": {"type": "integer"}
                            },
                            "required": ["name", "order_index"]
                        }
                    }
                },
                "required": ["destinations"]
            }
        }
    }
]

_EXTRACTION_PROMPT = (
    "From the travel itinerary below, extract only concrete places the user can visit.\n"
    "Return ONLY valid JSON, no markdown, no explanation.\n"
    "Do not include airports, hotels, transfers, meals, check-in, or generic activities.\n"
    "Maximum 8 destinations.\n"
    "Use null for unknown date/time fields.\n\n"
    "Required format:\n"
    "{\"destinations\": [{\"name\": \"...\", \"visit_date\": \"YYYY-MM-DD or null\", "
    "\"visit_start_time\": \"HH:MM or null\", \"visit_end_time\": \"HH:MM or null\", "
    "\"order_index\": 0}]}\n\n"
    "Itinerary:\n"
)

def _normalize_destinations(destinations: list[dict]) -> list[dict]:
    normalized = []
    for index, dest in enumerate(destinations):
        if not isinstance(dest, dict):
            continue

        name = dest.get("name")
        if not isinstance(name, str) or not name.strip():
            continue

        normalized.append(
            {
                "name": name.strip(),
                "visit_date": dest.get("visit_date"),
                "visit_start_time": dest.get("visit_start_time"),
                "visit_end_time": dest.get("visit_end_time"),
                "order_index": index,
            }
        )

    return normalized

def _extract_destinations_via_json(client, content: str) -> list[dict]:
    """
    Ask LLM to return destinations as JSON directly.
    """
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": _EXTRACTION_PROMPT + content}],
    )
    choice = response.choices[0]
    raw = choice.message.content or ""

    candidates = []
    stripped = raw.strip()
    if stripped:
        candidates.append(stripped)

    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
    if cleaned and cleaned not in candidates:
        candidates.append(cleaned)

    object_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if object_match:
        object_candidate = object_match.group().strip()
        if object_candidate not in candidates:
            candidates.append(object_candidate)

    array_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if array_match:
        array_candidate = array_match.group().strip()
        if array_candidate not in candidates:
            candidates.append(array_candidate)

    parsed = {}
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            break
        except json.JSONDecodeError:
            continue

    destinations = parsed.get("destinations", []) if isinstance(parsed, dict) else parsed
    if not isinstance(destinations, list):
        destinations = []
    return _normalize_destinations(destinations)


def _save_draft_to_redis(user_id: str, destinations: list[dict]) -> str | None:
    """
    Save destinations to Redis draft. Returns draft_id or None.
    """
    destinations = _normalize_destinations(destinations)
    if not destinations:
        return None
    redis = get_redis()
    if not redis:
        return None
    draft_id = str(uuid.uuid4())
    redis.setex(
        f"trip_draft:{user_id}:{draft_id}",
        1800,
        json.dumps(destinations, ensure_ascii=False)
    )
    return draft_id


def plan_trip_ai(
    user_id: str,
    user_query: str,
    trip_destinations: list[str] | None = None,
    use_web_search: bool = True,
    preferences: list[str] | None = None,
    thinking_process_toggle: bool = False,
    trip_days: int | None = None,
) -> dict:
    """
    CAG + RAG pipeline: preload user context optionally retrieve live info then call LLM
    """

    # CAG: preloaded user context (Redis cache or Supabase fallback)
    cag_ctx = build_user_context(user_id)
    system_prompt = build_system_prompt(cag_ctx)

    # RAG: live retrieval only when destinations are provided and Tavily is configured
    rag_text = ""
    if use_web_search and trip_destinations and settings.TAVILY_API_KEY:
        rag_query = build_rag_query(trip_destinations[0], user_query, preferences)
        rag_text = retrieve_place_context(trip_destinations, rag_query)

    user_message = build_user_message(user_query, rag_text)

    # Determine max_tokens
    if trip_days:
        days = trip_days
    else:
        match = re.search(r"(\d+)[\s-]*day", user_query, re.IGNORECASE)
        days = int(match.group(1)) if match else 0

    max_tokens = 8192 if days > 7 else 4096

    client = get_llm_client()

    if settings.LLM_PROVIDER == "gemini" and thinking_process_toggle:
        # Use native Gemini SDK to get thinking content
        from app.ai.gemini_native import generate_content_with_thinking
        result = generate_content_with_thinking(
            system_prompt=system_prompt,
            user_message=user_message,
            model=settings.LLM_MODEL,
            max_output_tokens=max_tokens,
        )
        content = result["content"]
        thinking_process = result["thinking"]
        # JSON extraction — Gemini OpenRouter doesn't support forced tool_choice
        destinations = _extract_destinations_via_json(client, content)
    else:
        thinking_process = None
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            tools=DESTINATION_TOOL,
            tool_choice="auto",
        )
        content = response.choices[0].message.content or ""
        tool_calls = response.choices[0].message.tool_calls if response else None
        if tool_calls:
            try:
                args = json.loads(tool_calls[0].function.arguments)
                destinations = args.get("destinations", [])
            except (json.JSONDecodeError, AttributeError, IndexError, KeyError, TypeError):
                destinations = []
        else:
            destinations = []

    draft_id = _save_draft_to_redis(user_id, destinations)
    return {"result": content, "thinking": thinking_process, "draft_id": draft_id}


def suggest_next_destination(user_id: str, current_trip_country: str) -> str:
    """
    CAG-only: suggest unvistied destinations based on travel history
    No web research needed - personalisation comes entirely from preloaded context
    """
    cag_ctx = build_user_context(user_id)
    system_prompt = build_system_prompt(cag_ctx)

    client = get_llm_client()
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        max_tokens=512,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"Based on my travel history, suggest 3 destinations in or near "
                f"{current_trip_country} that I haven't visited yet. "
                f"Give a one-sentence reason for each."
            )},
        ],
    )
    return response.choices[0].message.content


def chat_ai(
    user_id: str,
    message: str,
    conversation_id: str | None,
    destinations: list[str] | None,
    use_web_search: bool,
    thinking_process_toggle: bool,
):
    """
    Streaming chat with conversation history stored in Redis
    """
    redis = get_redis()
    chat_id = conversation_id or str(uuid.uuid4())
    history_key = f"chat:{user_id}:{chat_id}"

    # Load conversation history from Redis
    history = []
    if redis:
        raw = redis.get(history_key)
        if raw:
            history = json.loads(raw)

    # CAG: user context
    cag_ctx = build_user_context(user_id)
    system_prompt = build_system_prompt(cag_ctx, include_itinerary_flag=True)

    # Show thinking process
    if thinking_process_toggle:
        system_prompt += (
            "\n\nYOU MUST start your response with a <thinking> block. "
            "Format EXACTLY like this:\n"
            "<thinking>\nyour step-by-step reasoning here\n</thinking>\n\n"
            "Then provide your final answer after the closing tag."
            "\n\nBefore answering, wrap your reasoning inside <thinking>...</thinking> tags. "
            "Then provide your final answer outside the tags."
        )

    # RAG: only if destination provided
    rag_text = ""
    if use_web_search and destinations and settings.TAVILY_API_KEY:
        rag_text = retrieve_place_context(destinations, message)

    user_message = build_user_message(message, rag_text)

    # Build full message array
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    client = get_llm_client()
    stream = client.chat.completions.create(
        model=settings.LLM_MODEL,
        max_tokens=4096,
        messages=messages,
        stream=True,
    )

    # Stream and collect full response
    def generate():
        # First event: send conversation_id
        yield f"data: {json.dumps({'type': 'meta', 'conversation_id': chat_id})}\n\n"

        full_content = ""
        thinking_sent = False

        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            full_content += delta

            # Buffer until </thinking> is found, then switch to token streaming
            if thinking_process_toggle and not thinking_sent:
                if "</thinking>" in full_content:
                    match = re.search(r"<thinking>(.*?)</thinking>", full_content, re.DOTALL)
                    if match:
                        thinking_text = match.group(1).strip()
                        yield f"data: {json.dumps({'type': 'thinking', 'content': thinking_text})}\n\n"
                        remainder = full_content[match.end():].strip()
                        if remainder:
                            yield f"data: {json.dumps({'type': 'token', 'content': remainder})}\n\n"
                        thinking_sent = True
                continue

            if delta:
                yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"

        # Strip itinerary flag tags before saving to history
        clean_content = (
            full_content
            .replace("<has_itinerary>true</has_itinerary>", "")
            .replace("<has_itinerary>false</has_itinerary>", "")
            .strip()
        )

        # JSON extraction if itinerary detected
        if "<has_itinerary>true</has_itinerary>" in full_content:
            chat_destinations = _extract_destinations_via_json(client, clean_content)
            draft_id = _save_draft_to_redis(user_id, chat_destinations)
            if draft_id:
                yield f"data: {json.dumps({'type': 'draft', 'draft_id': draft_id})}\n\n"

        # Save history to Redis
        if redis:
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": clean_content})
            # Keep last 20 messages to avoid token overflow
            trimmed = history[-20:]
            redis.setex(history_key, 7200, json.dumps(trimmed, ensure_ascii=False))

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return generate()
