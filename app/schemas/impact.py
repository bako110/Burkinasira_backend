from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.impact import ImpactInitiativeCategory, ImpactInitiativeStatus


class CreateInitiativeRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    category: ImpactInitiativeCategory
    description: str = Field(..., min_length=10)
    region: Optional[str] = None
    cover_photo: Optional[str] = None


class UpdateInitiativeRequest(BaseModel):
    title: Optional[str] = None
    category: Optional[ImpactInitiativeCategory] = None
    description: Optional[str] = None
    region: Optional[str] = None
    is_verified: Optional[bool] = None
    cover_photo: Optional[str] = None
    status: Optional[ImpactInitiativeStatus] = None


class InitiativeResponse(BaseModel):
    id: str
    title: str
    category: ImpactInitiativeCategory
    description: str
    region: Optional[str] = None
    is_verified: bool
    cover_photo: Optional[str] = None
    supporter_count: int
    created_at: datetime


class CreateIndicatorRequest(BaseModel):
    label: str = Field(..., min_length=2, max_length=150)
    value: float
    unit: Optional[str] = None


class IndicatorResponse(BaseModel):
    id: str
    label: str
    value: float
    unit: Optional[str] = None
    updated_at: datetime


class SupportInitiativeRequest(BaseModel):
    message: Optional[str] = None
