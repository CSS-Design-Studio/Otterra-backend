from tavily import TavilyClient
from app.core.config import settings

def _get_tavily() -> TavilyClient:
    return TavilyClient(api_key=settings.TAVILY_API_KEY)

def retrieve_destination_info(destination: str, user_query: str) -> str:
    """
    RAG layer: live web search via Tavily for a given destination
    Use this for time-sensitive data: opening hours, events, safety advisories
    """
    client = _get_tavily()

    print(f"[RAG] Searching Tavily for: {destination} | query: {user_query}") 
    
    result = client.search(
        query = f"{destination} travel tips {user_query}",
        search_depth = "basic", # use "advanced" for deeper results (higher cost)
        max_results=10,
        include_answer=True, # Tavily generates a short summary on top of results
    )

    print(f"[RAG] Tavily answer: {result.get('answer', 'NO ANSWER')[:200]}")  

    answer = result.get("answer", "")
    snippets = "\n".join(
        f"- {r['title']}: {r['content'][:300]}"
        for r in result.get("results", [])
    )

    output = f"{answer}\n\n{snippets}".strip()
    return output or "No live information retrieved"

def retrieve_place_context(destinations: list[str], query: str) -> str:
    """
    Retrieve live info for the primary destination only
    Avoids multiple API calls when a trip has several destination
    """
    if not destinations:
        return ""
    return retrieve_destination_info(destinations[0], query)


# User's preferences

PREFERENCE_QUERY_MAP = {                                                                                                                                               
    "Popular":           "popular tourist attractions",                                                                                                                  
    "Museum":            "museums and art galleries",                                                                                                                    
    "Nature":            "nature parks and outdoor activities",                                                                                                          
    "Food":              "local food street food restaurants",                                                                                                           
    "History":           "historical sites and cultural heritage",                                                                                                       
    "Shopping":          "shopping districts markets souvenirs",                                                                                                         
    "Unique experience": "unique local experiences off the beaten path",                                                                                                 
}

def build_rag_query(
    destination: str, 
    user_query: str, 
    preferences: list[str] | None
) -> str:
    """
    Build a focued Tavily search query from destination, user query, and preferneces.
    Limit to top 3 preferences to avoid diluting search precision.
    """

    top_preferences = (preferences or [])[:5]
    preference_terms = " ".join(
        PREFERENCE_QUERY_MAP.get(p.capitalize(), p) for p in top_preferences
    )
    return f"{destination} {preference_terms} {user_query} travel guide".strip()

