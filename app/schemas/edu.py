from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint
from app.models.edu import EduOutingType, EduOutingStatus, EduBookingStatus


class CreateOutingRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    type: EduOutingType
    description: str = Field(..., min_length=10)
    region: str
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    target_level: Optional[str] = None
    price_per_participant: Optional[float] = None
    currency: str = "XOF"
    max_participants: Optional[int] = None


class UpdateOutingRequest(BaseModel):
    title: Optional[str] = None
    type: Optional[EduOutingType] = None
    description: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    target_level: Optional[str] = None
    price_per_participant: Optional[float] = None
    currency: Optional[str] = None
    max_participants: Optional[int] = None
    status: Optional[EduOutingStatus] = None


class OutingResponse(BaseModel):
    id: str
    organizer_id: str
    title: str
    type: EduOutingType
    description: str
    region: str
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    target_level: Optional[str] = None
    price_per_participant: Optional[float] = None
    currency: str
    max_participants: Optional[int] = None
    created_at: datetime


class CreateEduBookingRequest(BaseModel):
    outing_id: str
    group_name: str = Field(..., min_length=2, max_length=150)
    participant_count: int = Field(..., gt=0)


class EduBookingResponse(BaseModel):
    id: str
    outing_id: str
    booked_by: str
    group_name: str
    participant_count: int
    status: EduBookingStatus
    created_at: datetime


class AddEduParticipantRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    notes: Optional[str] = None


class EduParticipantResponse(BaseModel):
    id: str
    booking_id: str
    full_name: str
    notes: Optional[str] = None
