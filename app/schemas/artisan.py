from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.artisan import ProductCategory, FulfillmentMode, ArtisanStatus, ProductStatus


class CreateArtisanRequest(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=150)
    story: Optional[str] = None
    photo_url: Optional[str] = None
    region: str
    province: Optional[str] = None
    city: Optional[str] = None


class UpdateArtisanRequest(BaseModel):
    display_name: Optional[str] = None
    story: Optional[str] = None
    photo_url: Optional[str] = None
    region: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None


class ArtisanResponse(BaseModel):
    id: str
    user_id: str
    display_name: str
    story: Optional[str] = None
    photo_url: Optional[str] = None
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
    stock_quantity: Optional[int] = None
    fulfillment_mode: Optional[FulfillmentMode] = None
    status: Optional[ProductStatus] = None


class ProductSummary(BaseModel):
    id: str
    artisan_id: str
    name: str
    category: ProductCategory
    price: float
    currency: str
    photo: Optional[str] = None
    average_rating: float
    review_count: int
    in_stock: bool


class ProductDetail(BaseModel):
    id: str
    artisan_id: str
    name: str
    description: str
    category: ProductCategory
    price: float
    currency: str
    photos: List[str]
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


class OrderResponse(BaseModel):
    id: str
    buyer_id: str
    product_id: str
    quantity: int
    unit_price: float
    total_price: float
    currency: str
    fulfillment_mode: FulfillmentMode
    status: str
    created_at: datetime
