from datetime import datetime
from math import radians, cos, sin, asin, sqrt
from typing import Optional
from app.core.database import get_database
from app.schemas.home import (
    HomeFeedResponse,
    NearbyServiceSummary,
    TravelModeSummary,
    GlobalSearchResult,
    GlobalSearchResponse,
)
from app.services import destination_service, event_service, booking_service, trip_service

SEARCHABLE_COLLECTIONS = {
    "destination": ("destinations", "name", "description"),
    "hotel": ("hotels", "name", "description"),
    "restaurant": ("restaurants", "name", "description"),
    "guide": ("guide_profiles", "display_name", "bio"),
    "health_facility": ("health_facilities", "name", "description"),
    "event": ("events", "title", "description"),
    "experience": ("experiences", "title", "description"),
}


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


async def global_search(q: str, page_size: int = 20) -> GlobalSearchResponse:
    """Recherche globale multi-types : lieu, activité, hôtel, restaurant, pharmacie,
    hôpital, événement, guide, transport... (§2)."""
    db = get_database()
    results = []

    for item_type, (collection_name, title_field, desc_field) in SEARCHABLE_COLLECTIONS.items():
        docs = await db[collection_name].find({
            "$or": [
                {title_field: {"$regex": q, "$options": "i"}},
                {desc_field: {"$regex": q, "$options": "i"}},
            ]
        }).limit(5).to_list(length=5)
        for d in docs:
            results.append(GlobalSearchResult(
                item_type=item_type,
                item_id=str(d["_id"]),
                title=d.get(title_field, ""),
                subtitle=d.get("region") or d.get("city"),
            ))

    return GlobalSearchResponse(query=q, results=results[:page_size], total=len(results))


async def get_nearby_essential_services(lat: float, lng: float, radius_km: float = 5.0, limit: int = 10) -> list:
    """Services indispensables à proximité : santé, sécurité, argent, routes (§2)."""
    db = get_database()
    services = []

    sources = [
        ("health_facilities", "health_facility"),
        ("road_services", "road_service"),
        ("money_service_points", "money_service"),
    ]
    for collection_name, item_type in sources:
        docs = await db[collection_name].find({}).to_list(length=None)
        for d in docs:
            loc = d.get("location")
            if not loc:
                continue
            dist = _haversine_km(lat, lng, loc["latitude"], loc["longitude"])
            if dist <= radius_km:
                services.append((dist, NearbyServiceSummary(
                    id=str(d["_id"]), name=d["name"], type=item_type,
                    distance_label=f"{dist:.1f} km",
                )))

    services.sort(key=lambda x: x[0])
    return [s[1] for s in services[:limit]]


async def get_travel_mode(user_id: str) -> TravelModeSummary:
    """Mode voyage : réservations en cours, itinéraire, informations importantes (§2)."""
    bookings = await booking_service.list_my_bookings(user_id)
    upcoming = [b for b in bookings if b.status in ("pending", "confirmed")]

    trips = await trip_service.list_my_trips(user_id)
    active_trip = next((t for t in trips if t.status in ("planned", "in_progress")), None)

    return TravelModeSummary(
        active=bool(upcoming or active_trip),
        upcoming_bookings=upcoming[:5],
        active_trip_id=active_trip.id if active_trip else None,
        active_trip_title=active_trip.title if active_trip else None,
    )


async def get_home_feed(user_id: Optional[str], near_lat: Optional[float] = None, near_lng: Optional[float] = None) -> HomeFeedResponse:
    """Accueil intelligent : agrège suggestions, populaires, événements, services proches, mode voyage (§2)."""
    popular = await destination_service.list_destinations(page=1, page_size=8)

    suggested = popular  # personnalisation avancée réservée à FasoViva AI (§26) une fois le provider LLM configuré
    if user_id:
        trips = await trip_service.list_my_trips(user_id)
        region_pref = trips[0].region if trips and trips[0].region else None
        if region_pref:
            suggested = await destination_service.list_destinations(region=region_pref, page=1, page_size=8)

    upcoming_events = await event_service.list_events(upcoming_only=True, page=1, page_size=6)

    nearby_services = []
    if near_lat is not None and near_lng is not None:
        nearby_services = await get_nearby_essential_services(near_lat, near_lng)

    travel_mode = await get_travel_mode(user_id) if user_id else TravelModeSummary(active=False)

    return HomeFeedResponse(
        suggested_destinations=suggested.items,
        popular_destinations=popular.items,
        upcoming_events=upcoming_events.items,
        nearby_essential_services=nearby_services,
        travel_mode=travel_mode,
    )
