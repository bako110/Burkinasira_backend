from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.privacy import ConsentType


class SetConsentRequest(BaseModel):
    consent_type: ConsentType
    granted: bool


class ConsentResponse(BaseModel):
    consent_type: ConsentType
    granted: bool
    updated_at: datetime


class DataExportResponse(BaseModel):
    user: dict
    bookings: list
    trips: list
    community_posts: list
    generated_at: datetime


class CreateRetentionPolicyRequest(BaseModel):
    data_category: str = Field(..., min_length=2, max_length=100)
    retention_days: int = Field(..., gt=0)
    description: Optional[str] = None


class RetentionPolicyResponse(BaseModel):
    id: str
    data_category: str
    retention_days: int
    description: Optional[str] = None
    updated_at: datetime
