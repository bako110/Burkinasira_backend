from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.trip import TripThemeType, TripStatus, TripDayItem, TripDay, TripCollaborator


class CreateTripRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    themes: List[TripThemeType] = []
    region: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget_estimate: Optional[float] = None
    currency: str = "XOF"


class UpdateTripRequest(BaseModel):
    title: Optional[str] = None
    themes: Optional[List[TripThemeType]] = None
    region: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget_estimate: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[TripStatus] = None


class TripSummary(BaseModel):
    id: str
    title: str
    themes: List[TripThemeType]
    region: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: TripStatus
    budget_estimate: Optional[float] = None
    currency: str


class TripDetail(BaseModel):
    id: str
    owner_id: str
    title: str
    themes: List[TripThemeType]
    region: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget_estimate: Optional[float] = None
    currency: str
    days: List[TripDay]
    linked_booking_ids: List[str]
    collaborators: List[TripCollaborator]
    status: TripStatus
    created_at: datetime
    updated_at: datetime


class AddTripDayItemRequest(BaseModel):
    date: date
    item: TripDayItem


class RemoveTripDayItemRequest(BaseModel):
    date: date
    item_index: int = Field(..., ge=0)


class ShareTripRequest(BaseModel):
    user_id: str
    can_edit: bool = False
