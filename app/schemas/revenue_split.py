from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class CreateRevenueSplitRuleRequest(BaseModel):
    item_type: str
    provider_percent: float = Field(..., ge=0, le=100)
    guide_percent: float = Field(default=0.0, ge=0, le=100)
    community_percent: float = Field(default=0.0, ge=0, le=100)
    transport_percent: float = Field(default=0.0, ge=0, le=100)
    taxes_percent: float = Field(default=0.0, ge=0, le=100)
    platform_commission_percent: float = Field(..., ge=0, le=100)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def check_total(self):
        total = (
            self.provider_percent + self.guide_percent + self.community_percent
            + self.transport_percent + self.taxes_percent + self.platform_commission_percent
        )
        if round(total, 2) != 100.0:
            raise ValueError(f"La répartition doit totaliser 100% (actuellement {total}%)")
        return self


class RevenueSplitRuleResponse(BaseModel):
    id: str
    item_type: str
    provider_percent: float
    guide_percent: float
    community_percent: float
    transport_percent: float
    taxes_percent: float
    platform_commission_percent: float
    notes: Optional[str] = None
    updated_at: datetime


class RevenueSplitBreakdown(BaseModel):
    item_type: str
    total_amount: float
    currency: str
    provider_amount: float
    guide_amount: float
    community_amount: float
    transport_amount: float
    taxes_amount: float
    platform_commission_amount: float
