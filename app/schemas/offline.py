from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.offline import OfflinePackageType


class CreateOfflinePackageRequest(BaseModel):
    type: OfflinePackageType
    title: str = Field(..., min_length=2, max_length=200)
    region: Optional[str] = None
    related_destination_id: Optional[str] = None
    file_url: str
    file_size_mb: Optional[float] = None


class UpdateOfflinePackageRequest(BaseModel):
    title: Optional[str] = None
    region: Optional[str] = None
    file_url: Optional[str] = None
    file_size_mb: Optional[float] = None
    bump_version: bool = False


class OfflinePackageResponse(BaseModel):
    id: str
    type: OfflinePackageType
    title: str
    region: Optional[str] = None
    related_destination_id: Optional[str] = None
    file_url: str
    file_size_mb: Optional[float] = None
    version: int
    updated_at: datetime


class RegisterDownloadRequest(BaseModel):
    package_id: str


class UserDownloadResponse(BaseModel):
    package_id: str
    downloaded_version: int
    downloaded_at: datetime
    is_up_to_date: bool
