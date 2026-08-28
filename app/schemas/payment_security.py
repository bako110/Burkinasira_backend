from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.payment_security import TransactionStatus, SuspiciousActivityFlagType


class ConfirmTransactionRequest(BaseModel):
    booking_id: str
    amount: float = Field(..., gt=0)
    currency: str = "XOF"
    idempotency_key: str = Field(..., min_length=8)
    payment_method: Optional[str] = None


class TransactionResponse(BaseModel):
    id: str
    booking_id: str
    payer_id: str
    amount: float
    currency: str
    status: TransactionStatus
    payment_method: Optional[str] = None
    created_at: datetime


class FlagSuspiciousActivityRequest(BaseModel):
    transaction_id: Optional[str] = None
    type: SuspiciousActivityFlagType
    details: Optional[str] = None


class SuspiciousFlagResponse(BaseModel):
    id: str
    transaction_id: Optional[str] = None
    reporter_id: str
    type: SuspiciousActivityFlagType
    details: Optional[str] = None
    created_at: datetime
