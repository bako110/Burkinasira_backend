from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.schemas.destination import DestinationSummary
from app.schemas.event import EventSummary
from app.schemas.booking import BookingResponse


class NearbyServiceSummary(BaseModel):
    id: str
    name: str
    type: str  # ex: "health_facility", "road_service", "money_service"
    distance_label: Optional[str] = None


class TravelModeSummary(BaseModel):
    active: bool
    upcoming_bookings: List[BookingResponse] = []
    active_trip_id: Optional[str] = None
    active_trip_title: Optional[str] = None


class HomeFeedResponse(BaseModel):
    suggested_destinations: List[DestinationSummary]
    popular_destinations: List[DestinationSummary]
    upcoming_events: List[EventSummary]
    nearby_essential_services: List[NearbyServiceSummary]
    travel_mode: TravelModeSummary


class GlobalSearchResult(BaseModel):
    item_type: str
    item_id: str
    title: str
    subtitle: Optional[str] = None


class GlobalSearchResponse(BaseModel):
    query: str
    results: List[GlobalSearchResult]
    total: int
