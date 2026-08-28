from datetime import datetime
from bson import ObjectId
from app.core.database import get_database
from app.models.analytics import AnalyticsEventType
from app.schemas.analytics import (
    TopDestination,
    TopActivity,
    SeasonalityPoint,
    ConversionStats,
    TouristAnalyticsSummary,
    ProAnalyticsSummary,
)

EVENTS_COLLECTION = "analytics_events"


async def track_event(type: AnalyticsEventType, item_type: str = None, item_id: str = None, query: str = None, user_id: str = None) -> None:
    db = get_database()
    await db[EVENTS_COLLECTION].insert_one({
        "type": type.value if isinstance(type, AnalyticsEventType) else type,
        "item_type": item_type,
        "item_id": item_id,
        "query": query,
        "user_id": user_id,
        "created_at": datetime.utcnow(),
    })


async def get_tourist_summary(limit: int = 10) -> TouristAnalyticsSummary:
    db = get_database()

    view_pipeline = [
        {"$match": {"type": "view", "item_type": "destination"}},
        {"$group": {"_id": "$item_id", "view_count": {"$sum": 1}}},
        {"$sort": {"view_count": -1}},
        {"$limit": limit},
    ]
    view_results = await db[EVENTS_COLLECTION].aggregate(view_pipeline).to_list(length=limit)

    top_destinations = []
    for r in view_results:
        if not ObjectId.is_valid(r["_id"]):
            continue
        dest = await db["destinations"].find_one({"_id": ObjectId(r["_id"])})
        if dest:
            booking_count = await db["bookings"].count_documents({"item_type": "destination", "item_id": r["_id"]})
            top_destinations.append(TopDestination(
                destination_id=r["_id"], name=dest["name"], view_count=r["view_count"], booking_count=booking_count,
            ))

    booking_pipeline = [
        {"$match": {"item_type": {"$exists": True}, "item_id": {"$exists": True}}},
        {"$group": {"_id": {"item_type": "$item_type", "item_id": "$item_id"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    booking_results = await db["bookings"].aggregate(booking_pipeline).to_list(length=limit)
    top_activities = [
        TopActivity(
            item_type=r["_id"]["item_type"], item_id=r["_id"]["item_id"],
            title="", booking_count=r["count"],
        )
        for r in booking_results
    ]
    # Récupère les titres depuis les bookings eux-mêmes (déjà dénormalisés)
    for activity in top_activities:
        sample = await db["bookings"].find_one({"item_type": activity.item_type, "item_id": activity.item_id})
        if sample:
            activity.title = sample.get("item_title", "")

    seasonality_pipeline = [
        {"$match": {"created_at": {"$exists": True}}},
        {"$group": {"_id": {"$month": "$created_at"}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    seasonality_results = await db["bookings"].aggregate(seasonality_pipeline).to_list(length=12)
    seasonality = [SeasonalityPoint(month=r["_id"], booking_count=r["count"]) for r in seasonality_results]

    avg_budget_doc = await db["trips"].aggregate([
        {"$match": {"budget_estimate": {"$ne": None}}},
        {"$group": {"_id": None, "avg": {"$avg": "$budget_estimate"}}},
    ]).to_list(length=1)
    average_budget = avg_budget_doc[0]["avg"] if avg_budget_doc else None

    total_searches = await db[EVENTS_COLLECTION].count_documents({"type": "search"})
    total_bookings = await db["bookings"].count_documents({"item_type": {"$exists": True}})
    conversion_rate = round((total_bookings / total_searches) * 100, 2) if total_searches else 0.0

    return TouristAnalyticsSummary(
        top_destinations=top_destinations,
        top_activities=top_activities,
        seasonality=seasonality,
        average_budget=average_budget,
        conversion=ConversionStats(
            total_searches=total_searches, total_bookings=total_bookings, conversion_rate_percent=conversion_rate,
        ),
    )


async def get_pro_summary(provider_id: str) -> ProAnalyticsSummary:
    from app.services import pro_workspace_service
    dashboard = await pro_workspace_service.get_dashboard(provider_id)

    db = get_database()
    search_appearances = await db[EVENTS_COLLECTION].count_documents({"type": "view", "item_id": {"$exists": True}})

    return ProAnalyticsSummary(
        provider_id=provider_id,
        total_bookings=dashboard.total_bookings,
        total_revenue=dashboard.total_revenue,
        currency=dashboard.currency,
        average_rating=dashboard.average_rating,
        search_appearances=search_appearances,
    )
