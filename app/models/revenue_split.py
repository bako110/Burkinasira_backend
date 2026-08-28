from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RevenueSplitRule(BaseModel):
    """Règle contractuelle de répartition du prix payé, par type d'offre (§39)."""
    id: Optional[str] = Field(default=None, alias="_id")
    item_type: str  # ex: "experience", "guide", "hotel"
    provider_percent: float
    guide_percent: float = 0.0
    community_percent: float = 0.0
    transport_percent: float = 0.0
    taxes_percent: float = 0.0
    platform_commission_percent: float
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
