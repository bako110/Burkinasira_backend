from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.tourist_info import TravelInfoCategory, InfoSourceType


class CreateTravelInfoRequest(BaseModel):
    category: TravelInfoCategory
    title: str = Field(..., min_length=2, max_length=200)
    content: str = Field(..., min_length=5)
    source_type: InfoSourceType = InfoSourceType.OFFICIEL
    official_url: Optional[str] = None
    country_scope: str = "Burkina Faso"


class UpdateTravelInfoRequest(BaseModel):
    category: Optional[TravelInfoCategory] = None
    title: Optional[str] = None
    content: Optional[str] = None
    source_type: Optional[InfoSourceType] = None
    official_url: Optional[str] = None
    country_scope: Optional[str] = None


class TravelInfoResponse(BaseModel):
    id: str
    category: TravelInfoCategory
    title: str
    content: str
    source_type: InfoSourceType
    official_url: Optional[str] = None
    country_scope: str
    updated_at: datetime


class CreateDiplomaticContactRequest(BaseModel):
    country: str
    type: str = "ambassade"
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class UpdateDiplomaticContactRequest(BaseModel):
    country: Optional[str] = None
    type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class DiplomaticContactResponse(BaseModel):
    id: str
    country: str
    type: str
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
