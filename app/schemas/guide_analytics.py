from typing import List
from pydantic import BaseModel


class TimeSeriesPoint(BaseModel):
    period: str  # "2026-08-29" (jour), "2026-08" (mois), "2026" (année)
    customer_count: int
    booking_count: int
    revenue: float


class GuideAnalyticsSummary(BaseModel):
    currency: str
    total_customers: int
    total_bookings: int
    total_revenue: float
    average_booking_value: float
    completion_rate: float  # % de réservations complétées parmi confirmed+completed+cancelled
    daily: List[TimeSeriesPoint]
    monthly: List[TimeSeriesPoint]
    yearly: List[TimeSeriesPoint]
