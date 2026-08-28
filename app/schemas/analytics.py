from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class TopDestination(BaseModel):
    destination_id: str
    name: str
    view_count: int
    booking_count: int


class TopActivity(BaseModel):
    item_type: str
    item_id: str
    title: str
    booking_count: int


class SeasonalityPoint(BaseModel):
    month: int  # 1-12
    booking_count: int


class ProviderPerformance(BaseModel):
    provider_id: str
    total_bookings: int
    total_revenue: float
    average_rating: float


class ConversionStats(BaseModel):
    total_searches: int
    total_bookings: int
    conversion_rate_percent: float


class TouristAnalyticsSummary(BaseModel):
    top_destinations: List[TopDestination]
    top_activities: List[TopActivity]
    seasonality: List[SeasonalityPoint]
    average_budget: Optional[float] = None
    currency: str = "XOF"
    conversion: ConversionStats


class ProAnalyticsSummary(BaseModel):
    """Statistiques limitées à un professionnel — visibles depuis son espace pro (§35/§45)."""
    provider_id: str
    total_bookings: int
    total_revenue: float
    currency: str
    average_rating: float
    search_appearances: int
