from google import genai
from google.genai import types
from app.core.config import settings


def _normalize_model(model: str) -> str:
    """Remove 'google/' prefix if present, as native SDK uses model name directly"""
    if model.startswith("google/"):
        return model.split("/", 1)[1]
    return model


def generate_content_with_thinking(
    *,
    system_prompt: str,
    user_message: str,
    model: str,
    max_output_tokens: int,
) -> dict:
    """
    Call Gemini native SDK with thinking enabled.
    Returns {"content": str, "thinking": str | None}
    """
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    response = client.models.generate_content(
        model=_normalize_model(model),
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_output_tokens,
            thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_budget=settings.GEMINI_THINKING_BUDGET,
                ),
        ),
    )

    thoughts = []
    answer_parts = []

    for part in response.candidates[0].content.parts:
        if not part.text:
            continue
        if getattr(part, "thought", False):
            thoughts.append(part.text)
        else:
            answer_parts.append(part.text)

    return {
        "content": "\n".join(answer_parts).strip(),
        "thinking": "\n".join(thoughts).strip() or None,
    }
