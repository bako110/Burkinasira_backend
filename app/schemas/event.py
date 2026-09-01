from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource
from app.models.event import EventCategory, EventStatus, ProgramItem


class CreateEventRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str = Field(..., min_length=10)
    category: EventCategory
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    photos: List[str] = []
    start_date: datetime
    end_date: Optional[datetime] = None
    program: List[ProgramItem] = []
    ticket_price: Optional[float] = None
    currency: str = "XOF"
    requires_ticket: bool = False
    linked_hotel_ids: List[str] = []
    linked_transport_provider_ids: List[str] = []


class UpdateEventRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[EventCategory] = None
    region: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    address: Optional[str] = None
    photos: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    program: Optional[List[ProgramItem]] = None
    ticket_price: Optional[float] = None
    currency: Optional[str] = None
    requires_ticket: Optional[bool] = None
    linked_hotel_ids: Optional[List[str]] = None
    linked_transport_provider_ids: Optional[List[str]] = None
    status: Optional[EventStatus] = None


class EventSummary(BaseModel):
    id: str
    title: str
    slug: str
    category: EventCategory
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    photo: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    ticket_price: Optional[float] = None
    currency: str
    requires_ticket: bool


class EventDetail(BaseModel):
    id: str
    organizer_id: str
    title: str
    slug: str
    description: str
    category: EventCategory
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    photos: List[str]
    start_date: datetime
    end_date: Optional[datetime] = None
    program: List[ProgramItem]
    ticket_price: Optional[float] = None
    currency: str
    requires_ticket: bool
    linked_hotel_ids: List[str]
    linked_transport_provider_ids: List[str]
    data_source: DataSource
    created_at: datetime
    updated_at: datetime


class EventListResponse(BaseModel):
    items: List[EventSummary]
    total: int
    page: int
    page_size: int
