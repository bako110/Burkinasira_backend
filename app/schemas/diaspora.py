from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint
from app.models.diaspora import DiasporaContentType, CommunityMeetupStatus


class CreateDiasporaContentRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    type: DiasporaContentType
    description: str = Field(..., min_length=10)
    region: Optional[str] = None
    location: Optional[GeoPoint] = None
    related_destination_id: Optional[str] = None


class UpdateDiasporaContentRequest(BaseModel):
    title: Optional[str] = None
    type: Optional[DiasporaContentType] = None
    description: Optional[str] = None
    region: Optional[str] = None
    location: Optional[GeoPoint] = None
    related_destination_id: Optional[str] = None


class DiasporaContentResponse(BaseModel):
    id: str
    title: str
    type: DiasporaContentType
    description: str
    region: Optional[str] = None
    location: Optional[GeoPoint] = None
    related_destination_id: Optional[str] = None
    created_at: datetime


class CreateMeetupRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    region: str
    location: Optional[GeoPoint] = None
    scheduled_at: datetime


class MeetupResponse(BaseModel):
    id: str
    organizer_id: str
    title: str
    description: Optional[str] = None
    region: str
    location: Optional[GeoPoint] = None
    scheduled_at: datetime
    status: CommunityMeetupStatus
    participant_ids: List[str]
