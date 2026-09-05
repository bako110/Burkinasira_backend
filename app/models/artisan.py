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


class DeliveryAgency(BaseModel):
    """Agence de livraison à qui sont confiées les commandes artisanales (§19)."""
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    covered_regions: List[str] = []  # régions desservies ; vide = toutes
    # Compte utilisateur (facultatif) autorisé à consulter les commandes de
    # l'agence et à faire avancer leur statut de livraison.
    manager_user_id: Optional[str] = None
    active: bool = True
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
    agency_id: Optional[str] = None  # agence de livraison assignée à cette région
    delivery_provider: Optional[str] = None  # libellé dénormalisé (nom de l'agence)
    free_delivery_threshold: Optional[float] = Field(default=None, ge=0)
    eta_days_min: Optional[int] = Field(default=None, ge=0)
    eta_days_max: Optional[int] = Field(default=None, ge=0)
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        use_enum_values = True


class ArtisanOrderStatus(str, Enum):
    """Cycle de vie d'une commande artisanale."""
    PENDING = "pending"                # créée, paiement/confirmation en attente
    CONFIRMED = "confirmed"            # confirmée par l'artisan / la plateforme
    HANDED_TO_AGENCY = "handed_to_agency"  # colis remis à l'agence de livraison
    IN_DELIVERY = "in_delivery"        # en cours de livraison
    DELIVERED = "delivered"            # livrée au client
    CANCELLED = "cancelled"            # annulée (stock réapprovisionné)
    RETURNED = "returned"              # retour after livraison (stock réapprovisionné)


# Transitions autorisées du statut de commande.
ARTISAN_ORDER_TRANSITIONS: dict = {
    ArtisanOrderStatus.PENDING.value: {
        ArtisanOrderStatus.CONFIRMED.value,
        ArtisanOrderStatus.CANCELLED.value,
    },
    ArtisanOrderStatus.CONFIRMED.value: {
        ArtisanOrderStatus.HANDED_TO_AGENCY.value,
        ArtisanOrderStatus.DELIVERED.value,  # retrait en main propre / livraison directe
        ArtisanOrderStatus.CANCELLED.value,
    },
    ArtisanOrderStatus.HANDED_TO_AGENCY.value: {
        ArtisanOrderStatus.IN_DELIVERY.value,
        ArtisanOrderStatus.CANCELLED.value,
    },
    ArtisanOrderStatus.IN_DELIVERY.value: {
        ArtisanOrderStatus.DELIVERED.value,
        ArtisanOrderStatus.RETURNED.value,
    },
    ArtisanOrderStatus.DELIVERED.value: {
        ArtisanOrderStatus.RETURNED.value,
    },
    ArtisanOrderStatus.CANCELLED.value: set(),
    ArtisanOrderStatus.RETURNED.value: set(),
}

# Statuts qui restituent le stock (une seule fois).
ARTISAN_ORDER_STOCK_RESTORING = {
    ArtisanOrderStatus.CANCELLED.value,
    ArtisanOrderStatus.RETURNED.value,
}


class DeliverySettlementStatus(str, Enum):
    """État du règlement des frais de livraison à l'agence."""
    PENDING = "pending"    # dû à l'agence, non réglé
    SETTLED = "settled"    # réglé
    NOT_APPLICABLE = "not_applicable"  # commande en retrait, aucun frais
