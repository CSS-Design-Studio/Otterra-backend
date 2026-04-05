from functools import lru_cache
from openai import OpenAI
from app.core.config import settings

# Map provider name -> (base_url, api_key)
# Add a new provider here without changing any other file.
_PROVIDER_CONFIG: dict[str, tuple[str, str]] = {
    "openrouter": (
        "https://openrouter.ai/api/v1",
        settings.OPENROUTER_API_KEY,
    ),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        settings.GEMINI_API_KEY,
    ),
    "groq": (
        "https://api.groq.com/openai/v1",
        settings.GROQ_API_KEY,
    ),
    "openai": (
        "https://api.openai.com/v1",
        settings.OPENAI_API_KEY,
    ),
    "ollama": (
        settings.OLLAMA_BASE_URL,
        "ollama",   # ollama doesn't require a real key
    ),
}

@lru_cache(maxsize=1)
def get_llm_client() -> OpenAI:
    """
      Returns an OpenAI-compatible client for the configured provider.
      All supported providers implement the OpenAI chat/completions API format.
      Switch provider by changing LLM_PROVIDER in .env 
    """
    provider = settings.LLM_PROVIDER
    if provider not in _PROVIDER_CONFIG:
        supported = ", ".join(_PROVIDER_CONFIG.keys())
        raise ValueError(f"Unsupported LLM_PROVIDER: '{provider}'. Supported: {supported}")
    
    base_url, api_key = _PROVIDER_CONFIG[provider]
    return OpenAI(base_url = base_url, api_key=api_key)



    

