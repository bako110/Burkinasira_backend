from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentTransaction(BaseModel):
    """Confirmation de transaction et historique des paiements (§40)."""
    id: Optional[str] = Field(default=None, alias="_id")
    booking_id: str
    payer_id: str
    amount: float
    currency: str = "XOF"
    status: TransactionStatus = TransactionStatus.PENDING
    idempotency_key: str  # protection double paiement
    payment_method: Optional[str] = None  # ex: "wallet", "mobile_money"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class SuspiciousActivityFlagType(str, Enum):
    DUPLICATE_PAYMENT_ATTEMPT = "duplicate_payment_attempt"
    UNUSUAL_AMOUNT = "unusual_amount"
    RAPID_SUCCESSIVE_ATTEMPTS = "rapid_successive_attempts"
    OTHER = "other"


class SuspiciousPaymentFlag(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    transaction_id: Optional[str] = None
    reporter_id: str
    type: SuspiciousActivityFlagType
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
