from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ProductCategory(str, Enum):
    TISSUS_VETEMENTS = "tissus_vetements"
    BIJOUX = "bijoux"
    POTERIE = "poterie"
    SCULPTURE = "sculpture"
    OBJET_ART = "objet_art"
    PRODUIT_AGRICOLE = "produit_agricole"
    PRODUIT_ALIMENTAIRE = "produit_alimentaire"
    SOUVENIR = "souvenir"


class FulfillmentMode(str, Enum):
    LIVRAISON = "livraison"
    RETRAIT = "retrait"
    LES_DEUX = "les_deux"


class ArtisanStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Artisan(BaseModel):
    """Profil artisan vérifié (§19)."""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    display_name: str
    story: Optional[str] = None  # histoire du fabricant
    photo_url: Optional[str] = None
    photos: List[str] = []
    videos: List[str] = []
    region: str
    province: Optional[str] = None
    city: Optional[str] = None
    is_verified: bool = False
    status: ArtisanStatus = ArtisanStatus.PENDING
    average_rating: float = 0.0
    review_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class ProductStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    OUT_OF_STOCK = "out_of_stock"
    ARCHIVED = "archived"


class Product(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    artisan_id: str
    name: str
    description: str
    category: ProductCategory
    price: float
    currency: str = "XOF"
    photos: List[str] = []
    videos: List[str] = []
    stock_quantity: int = 0
    fulfillment_mode: FulfillmentMode = FulfillmentMode.LES_DEUX
    average_rating: float = 0.0
    review_count: int = 0
    status: ProductStatus = ProductStatus.PUBLISHED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class DeliveryFeeRule(BaseModel):
    """Grille des frais de livraison des produits artisanaux (§19).

    Les commandes en mode « livraison » sont confiées à une agence de livraison ;
    les frais sont calculés automatiquement à partir de cette grille selon la
    région de destination du client, puis reversés à l'agence.
    """
    id: Optional[str] = Field(default=None, alias="_id")
    region: str  # région de destination ; "*" = tarif par défaut
    fee: float = Field(..., ge=0)  # frais fixes pour cette région
    currency: str = "XOF"
    delivery_provider: Optional[str] = None  # agence de livraison assignée
    free_delivery_threshold: Optional[float] = Field(default=None, ge=0)
    eta_days_min: Optional[int] = Field(default=None, ge=0)
    eta_days_max: Optional[int] = Field(default=None, ge=0)
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True
