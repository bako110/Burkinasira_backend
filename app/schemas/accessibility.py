from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint
from app.models.accessibility import AccessibilityReportStatus


class ReportObstacleRequest(BaseModel):
    location: GeoPoint
    description: str = Field(..., min_length=5)
    related_destination_id: Optional[str] = None


class ObstacleReportResponse(BaseModel):
    id: str
    reporter_id: str
    location: GeoPoint
    description: str
    related_destination_id: Optional[str] = None
    status: AccessibilityReportStatus
    created_at: datetime


class ModerateObstacleRequest(BaseModel):
    status: AccessibilityReportStatus
