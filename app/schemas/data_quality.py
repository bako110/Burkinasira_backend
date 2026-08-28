from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.data_quality import DataErrorReportStatus


class ReportDataErrorRequest(BaseModel):
    item_type: str
    item_id: str
    description: str = Field(..., min_length=5)


class DataErrorReportResponse(BaseModel):
    id: str
    reporter_id: str
    item_type: str
    item_id: str
    description: str
    status: DataErrorReportStatus
    created_at: datetime


class ModerateDataErrorRequest(BaseModel):
    status: DataErrorReportStatus


class DuplicateCandidateResponse(BaseModel):
    id: str
    item_type: str
    item_id_a: str
    item_id_b: str
    similarity_score: float
    resolved: bool


class ResolveDuplicateRequest(BaseModel):
    resolved: bool = True


class DataChangeLogResponse(BaseModel):
    id: str
    item_type: str
    item_id: str
    changed_by: str
    change_summary: str
    created_at: datetime
