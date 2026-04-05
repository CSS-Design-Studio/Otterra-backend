def build_system_prompt(cag_context: dict, include_itinerary_flag: bool = False) -> str:
    """
    Build the system prompt by concatenate the preloaded CAG context
    This is what makes the model personalised without any retrieval step
    """

    user_name = cag_context["user"]["name"]
    visited = ", ".join(cag_context["visited_places"]) or "none yet"

    past_trips_text = ""
    for trip in cag_context["past_trips"][:5]:  # cap at 5 to stay within token budget
        dests = ", ".join(trip["destinations"]) or "no destinations added"
        past_trips_text += (
            f"  - {trip['title']} ({trip['status']}): {dests} | "
            f"Budget: {trip['budget']}\n"
        )
    
    base = f"""You are a personal solo travel planning assistant for {user_name}.
    ## User Context (preloaded)
    - Name: {user_name}
    - Places already visited: {visited}
    - Recent trips:
    {past_trips_text or "  No trips yet."}

    ## Your Role
    - Give personalized advice based on the user's travel history
    - Avoid recommending places they have already visited, unless explicitly asked
    - Suggest options that fit the user's typical budget range
    - Be concise, practical, and specific — not generic travel blog content
    - If live search results are provided below, use them to ground your answer in current facts
    - Use the live search results as supplementary facts only. Always provide a complete, detailed itinerary regardless.
    - You MUST reply in the exact same language (Just based on the language of the query not the departure place!) the user uses in their question. If the user writes in English, reply in English. If in Traditional Chinese, reply in Traditional Chinese. If in Simplified Chinese, reply in Simplified Chinese, unless they ask you reply in certain language.
    """

    if include_itinerary_flag:
        base += (
            "\n\nIf your response contains a travel itinerary with specific days or destinations, "
            "end your response with: <has_itinerary>true</has_itinerary>\n"
            "Otherwise end with: <has_itinerary>false</has_itinerary>"
        )

    return base

def build_user_message(user_query: str, rag_context: str = "") ->  str:
    """
    Combined the user's question with RAG-retrived live information
    If no RAG context, returns the query as-is
    """

    if rag_context:
        return (
            f"## Live Search Results\n{rag_context}\n\n"
            f"## User Question\n{user_query}"
        )
    return user_query