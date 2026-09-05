from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.artisan import (
    ProductCategory,
    FulfillmentMode,
    ArtisanStatus,
    ProductStatus,
    ArtisanOrderStatus,
    DeliverySettlementStatus,
)


class CreateArtisanRequest(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=150)
    story: Optional[str] = None
    photo_url: Optional[str] = None
    photos: List[str] = []
    videos: List[str] = []
    region: str
    province: Optional[str] = None
    city: Optional[str] = None


class UpdateArtisanRequest(BaseModel):
    display_name: Optional[str] = None
    story: Optional[str] = None
    photo_url: Optional[str] = None
    photos: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    region: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None


class ArtisanResponse(BaseModel):
    id: str
    user_id: str
    display_name: str
    story: Optional[str] = None
    photo_url: Optional[str] = None
    photos: List[str] = []
    videos: List[str] = []
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    is_verified: bool
    status: ArtisanStatus
    average_rating: float
    review_count: int
    created_at: datetime


class CreateProductRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: str = Field(..., min_length=5)
    category: ProductCategory
    price: float = Field(..., gt=0)
    currency: str = "XOF"
    photos: List[str] = []
    videos: List[str] = []
    stock_quantity: int = Field(default=0, ge=0)
    fulfillment_mode: FulfillmentMode = FulfillmentMode.LES_DEUX
    artisan_id: Optional[str] = None


class UpdateProductRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ProductCategory] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    photos: Optional[List[str]] = None
    videos: Optional[List[str]] = None
    stock_quantity: Optional[int] = None
    fulfillment_mode: Optional[FulfillmentMode] = None
    status: Optional[ProductStatus] = None


class ProductSummary(BaseModel):
    id: str
    artisan_id: str
    name: str
    slug: str
    category: ProductCategory
    price: float
    currency: str
    photo: Optional[str] = None
    average_rating: float
    review_count: int
    in_stock: bool
    stock_quantity: int


class ProductDetail(BaseModel):
    id: str
    artisan_id: str
    name: str
    slug: str
    description: str
    category: ProductCategory
    price: float
    currency: str
    photos: List[str]
    videos: List[str]
    stock_quantity: int
    fulfillment_mode: FulfillmentMode
    average_rating: float
    review_count: int
    status: ProductStatus
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    items: List[ProductSummary]
    total: int
    page: int
    page_size: int


class CreateOrderRequest(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)
    fulfillment_mode: FulfillmentMode
    # Région de destination — obligatoire en mode livraison, sert au calcul
    # automatique des frais de livraison (agence de livraison).
    delivery_region: Optional[str] = None
    delivery_address: Optional[str] = None


class OrderStatusEvent(BaseModel):
    status: str
    at: datetime
    by: Optional[str] = None  # user id de l'acteur
    note: Optional[str] = None


class OrderResponse(BaseModel):
    id: str
    buyer_id: str
    product_id: str
    artisan_id: Optional[str] = None
    quantity: int
    unit_price: float
    subtotal: float
    delivery_fee: float
    delivery_region: Optional[str] = None
    delivery_address: Optional[str] = None
    agency_id: Optional[str] = None
    delivery_provider: Optional[str] = None
    delivery_eta_days_min: Optional[int] = None
    delivery_eta_days_max: Optional[int] = None
    tracking_number: Optional[str] = None
    carrier_note: Optional[str] = None
    estimated_delivery_date: Optional[datetime] = None
    settlement_status: Optional[str] = None
    total_price: float
    currency: str
    fulfillment_mode: FulfillmentMode
    status: str
    status_history: List[OrderStatusEvent] = []
    created_at: datetime
    updated_at: Optional[datetime] = None


class UpdateOrderStatusRequest(BaseModel):
    status: ArtisanOrderStatus
    tracking_number: Optional[str] = None
    carrier_note: Optional[str] = None
    estimated_delivery_date: Optional[datetime] = None
    note: Optional[str] = None


# --- Agences de livraison (§19) ---

class CreateDeliveryAgencyRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    covered_regions: List[str] = []
    manager_user_id: Optional[str] = None
    active: bool = True


class UpdateDeliveryAgencyRequest(BaseModel):
    name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    covered_regions: Optional[List[str]] = None
    manager_user_id: Optional[str] = None
    active: Optional[bool] = None


class DeliveryAgencyResponse(BaseModel):
    id: str
    name: str
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    covered_regions: List[str] = []
    manager_user_id: Optional[str] = None
    active: bool
    created_at: datetime
    updated_at: datetime


# --- Grille des frais de livraison (§19) ---

class UpsertDeliveryFeeRuleRequest(BaseModel):
    region: str = Field(..., min_length=1, max_length=100, description='Région de destination ; "*" pour le tarif par défaut')
    fee: float = Field(..., ge=0)
    currency: str = "XOF"
    agency_id: Optional[str] = Field(default=None, description="Agence de livraison assignée à cette région")
    free_delivery_threshold: Optional[float] = Field(default=None, ge=0)
    eta_days_min: Optional[int] = Field(default=None, ge=0)
    eta_days_max: Optional[int] = Field(default=None, ge=0)
    active: bool = True


class DeliveryFeeRuleResponse(BaseModel):
    id: str
    region: str
    fee: float
    currency: str
    agency_id: Optional[str] = None
    delivery_provider: Optional[str] = None
    free_delivery_threshold: Optional[float] = None
    eta_days_min: Optional[int] = None
    eta_days_max: Optional[int] = None
    active: bool
    updated_at: datetime


class DeliveryFeeQuoteRequest(BaseModel):
    region: str = Field(..., min_length=1, max_length=100)
    subtotal: float = Field(..., ge=0)


class DeliveryFeeQuote(BaseModel):
    region: str
    matched_region: str  # région réellement appliquée ("*" si tarif par défaut)
    subtotal: float
    delivery_fee: float
    free_delivery_applied: bool
    total: float
    currency: str
    agency_id: Optional[str] = None
    delivery_provider: Optional[str] = None
    eta_days_min: Optional[int] = None
    eta_days_max: Optional[int] = None


# --- Règlements des frais de livraison aux agences (§19) ---

class DeliveryDueLine(BaseModel):
    agency_id: Optional[str] = None
    agency_name: Optional[str] = None
    currency: str
    order_count: int
    total_due: float
    order_ids: List[str] = []


class DeliveryDueResponse(BaseModel):
    lines: List[DeliveryDueLine]
    grand_total: float


class CreateSettlementRequest(BaseModel):
    agency_id: str
    order_ids: List[str] = Field(..., min_length=1)
    reference: Optional[str] = None  # référence du virement / paiement
    note: Optional[str] = None


class SettlementResponse(BaseModel):
    id: str
    agency_id: str
    agency_name: Optional[str] = None
    currency: str
    order_ids: List[str]
    order_count: int
    total_amount: float
    reference: Optional[str] = None
    note: Optional[str] = None
    settled_by: Optional[str] = None
    created_at: datetime
