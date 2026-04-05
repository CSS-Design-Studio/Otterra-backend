import json
from app.db.redis import get_redis
from app.db.supabase import get_supabase

#Cache TTL: 15 minutes. Invalidate manually after profile/trip updates
CAG_TTL = 900

def build_user_context(user_id: str) -> dict:
    """
    CAG layer: preload bounded user-spcific data into a context blob.
    Tries Redis cache first; falls back to Supabase if cache is empty.
    """
    redis = get_redis()
    cache_key = f"cag:user:{user_id}"

    # Try cache first
    if redis:
        cached = redis.get(cache_key)
        if cached:
            return json.loads(cached)
    
    supabase = get_supabase()

    # Fetch user profile
    user_resp = supabase.table("users").select(
        "username, first_name, last_name"
    ).eq("id", user_id).single().execute()
    user = user_resp.data or {}

    # Fetch last 10 trips with destinations
    trip_resp = supabase.table("trips").select(
        "title, description, start_date, end_date, status, "
        "budget_amount, budget_currency, "
        "trip_destinations(name, description, address, latitude, longitude, notes)"
    ).eq("owner_id", user_id).in_(
        "status", ["completed", "planning", "ongoing"]
    ).order("created_at", desc=True).limit(10).execute()

    trips = trip_resp.data or []

    first = user.get("first_name", "")
    last = user.get("last_name", "")
    display_name = user.get("username", "Traveler") or f"{first} {last}".strip() or "Traveler"

    context = {
        "user": {
            "name": display_name,
        },
        "past_trips": [
            {
                "title": t["title"],
                "status": t["status"],
                "dates": f"{t.get('start_date')} to {t.get('end_date')}",
                "budget": f"{t.get('budget_amount')} {t.get('budget_currency', 'USD')}",
                "destinations": [
                    d["name"] for d in (t.get("trip_destinations") or [])
                ],
            }
            for t in trips
        ],
        # Only places from completed trips count as truly "visited"
        "visited_places": list({
            d["name"]
            for t in trips if t["status"] == "completed"
            for d in (t.get("trip_destinations") or [])
        }),
    }

    # Store in Redis
    if redis:
        redis.setex(cache_key, CAG_TTL, json.dumps(context, ensure_ascii=False))

    return context

def invalidate_user_context(user_id: str) -> None:
    """
    Clear the CAG cache for a user
    Call this after: profile update, trip create/delete, trip status -> completed
    """
    redis = get_redis()
    if redis:
        redis.delete(f"cag:user:{user_id}")
