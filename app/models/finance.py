from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource, OpeningHours


class MoneyServiceType(str, Enum):
    BANQUE = "banque"
    DISTRIBUTEUR = "distributeur"
    MOBILE_MONEY = "mobile_money"
    BUREAU_CHANGE = "bureau_change"


class MoneyServiceStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class MoneyServicePoint(BaseModel):
    """Banque, DAB, point Mobile Money ou bureau de change référencé."""
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    type: MoneyServiceType
    operator: Optional[str] = None  # ex: "Orange Money", "Coris Bank"
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    opening_hours: List[OpeningHours] = []
    contact_phone: Optional[str] = None
    status: MoneyServiceStatus = MoneyServiceStatus.PUBLISHED
    data_source: DataSource = DataSource()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class WalletTransactionType(str, Enum):
    TOPUP = "topup"
    PAYMENT = "payment"
    REFUND = "refund"
    WITHDRAWAL = "withdrawal"


class WalletTransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class Wallet(BaseModel):
    """Portefeuille BurkinaSira (§13, lecture seule au Lot 1)."""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    balance: float = 0.0
    currency: str = "XOF"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class WalletTransaction(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    wallet_id: str
    user_id: str
    type: WalletTransactionType
    amount: float
    currency: str = "XOF"
    status: WalletTransactionStatus = WalletTransactionStatus.PENDING
    description: Optional[str] = None
    reference: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class ExchangeRate(BaseModel):
    """Taux de change indicatif pour le convertisseur de devises."""
    id: Optional[str] = Field(default=None, alias="_id")
    base_currency: str = "XOF"
    target_currency: str
    rate: float  # 1 base_currency = rate target_currency
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
