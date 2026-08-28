from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.operator import OperatorCategory, OperatorApplicationStatus


class CreateOperatorApplicationRequest(BaseModel):
    category: OperatorCategory
    business_name: str = Field(..., min_length=2, max_length=150)
    documents: List[str] = []
    notes: Optional[str] = None


class ReviewOperatorApplicationRequest(BaseModel):
    status: OperatorApplicationStatus
    review_notes: Optional[str] = None


class OperatorApplicationResponse(BaseModel):
    id: str
    applicant_id: str
    category: OperatorCategory
    business_name: str
    documents: List[str]
    notes: Optional[str] = None
    status: OperatorApplicationStatus
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime
