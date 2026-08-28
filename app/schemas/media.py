from typing import Optional
from pydantic import BaseModel


class MediaUploadResponse(BaseModel):
    url: str
    resource_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
