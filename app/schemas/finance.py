from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.destination import GeoPoint, DataSource, OpeningHours
from app.models.finance import MoneyServiceType, MoneyServiceStatus, WalletTransactionType, WalletTransactionStatus


class CreateMoneyServiceRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    type: MoneyServiceType
    operator: Optional[str] = None
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    opening_hours: List[OpeningHours] = []
    contact_phone: Optional[str] = None


class UpdateMoneyServiceRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[MoneyServiceType] = None
    operator: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    location: Optional[GeoPoint] = None
    address: Optional[str] = None
    opening_hours: Optional[List[OpeningHours]] = None
    contact_phone: Optional[str] = None
    status: Optional[MoneyServiceStatus] = None


class MoneyServiceSummary(BaseModel):
    id: str
    name: str
    slug: str
    type: MoneyServiceType
    operator: Optional[str] = None
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint


class MoneyServiceDetail(BaseModel):
    id: str
    name: str
    slug: str
    type: MoneyServiceType
    operator: Optional[str] = None
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    location: GeoPoint
    address: Optional[str] = None
    opening_hours: List[OpeningHours]
    contact_phone: Optional[str] = None
    data_source: DataSource
    created_at: datetime
    updated_at: datetime


class MoneyServiceListResponse(BaseModel):
    items: List[MoneyServiceSummary]
    total: int
    page: int
    page_size: int


class CurrencyConversionRequest(BaseModel):
    amount: float
    from_currency: str = "XOF"
    to_currency: str


class CurrencyConversionResponse(BaseModel):
    amount: float
    from_currency: str
    to_currency: str
    rate: float
    converted_amount: float
    rate_updated_at: datetime


class WalletResponse(BaseModel):
    id: str
    user_id: str
    balance: float
    currency: str
    updated_at: datetime


class WalletTransactionResponse(BaseModel):
    id: str
    type: WalletTransactionType
    amount: float
    currency: str
    status: WalletTransactionStatus
    description: Optional[str] = None
    reference: Optional[str] = None
    created_at: datetime
