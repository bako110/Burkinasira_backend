from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.utils.slug import generate_unique_slug, find_by_slug_or_id, ensure_slug_index
from app.models.artisan import (
    ProductCategory,
    ArtisanStatus,
    ProductStatus,
    FulfillmentMode,
    ArtisanOrderStatus,
    ARTISAN_ORDER_TRANSITIONS,
    ARTISAN_ORDER_STOCK_RESTORING,
    DeliverySettlementStatus,
)
from app.services import delivery_fee_service
from app.schemas.artisan import (
    CreateArtisanRequest,
    UpdateArtisanRequest,
    ArtisanResponse,
    CreateProductRequest,
    UpdateProductRequest,
    ProductSummary,
    ProductDetail,
    ProductListResponse,
    CreateOrderRequest,
    OrderResponse,
    OrderStatusEvent,
    UpdateOrderStatusRequest,
)

ARTISANS_COLLECTION = "artisans"
PRODUCTS_COLLECTION = "artisan_products"
ORDERS_COLLECTION = "artisan_orders"


# --- Artisans ---

def _artisan_to_response(doc: dict) -> ArtisanResponse:
    return ArtisanResponse(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        display_name=doc["display_name"],
        story=doc.get("story"),
        photo_url=doc.get("photo_url"),
        photos=doc.get("photos", []),
        videos=doc.get("videos", []),
        region=doc["region"],
        province=doc.get("province"),
        city=doc.get("city"),
        is_verified=doc.get("is_verified", False),
        status=doc.get("status", ArtisanStatus.PENDING.value),
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
        created_at=doc["created_at"],
    )


async def create_artisan(data: CreateArtisanRequest, user_id: str) -> ArtisanResponse:
    db = get_database()
    existing = await db[ARTISANS_COLLECTION].find_one({"user_id": user_id})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un profil artisan existe déjà pour ce compte")

    now = datetime.utcnow()
    doc = data.model_dump()
    doc["user_id"] = user_id
    doc["is_verified"] = False
    doc["status"] = ArtisanStatus.PENDING.value
    doc["average_rating"] = 0.0
    doc["review_count"] = 0
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[ARTISANS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _artisan_to_response(doc)


async def list_artisans(
    region: Optional[str] = None,
    province: Optional[str] = None,
    verified_only: bool = False,
    include_all_statuses: bool = False,
) -> list:
    db = get_database()
    query: dict = {} if include_all_statuses else {"status": ArtisanStatus.ACTIVE.value}
    if region:
        query["region"] = region
    if province:
        query["province"] = province
    if verified_only:
        query["is_verified"] = True
    docs = await db[ARTISANS_COLLECTION].find(query).to_list(length=None)
    return [_artisan_to_response(d) for d in docs]


async def get_artisan(artisan_id: str) -> ArtisanResponse:
    db = get_database()
    if not ObjectId.is_valid(artisan_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artisan introuvable")
    doc = await db[ARTISANS_COLLECTION].find_one({"_id": ObjectId(artisan_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artisan introuvable")
    return _artisan_to_response(doc)


async def get_artisan_by_user_id(user_id: str) -> ArtisanResponse:
    db = get_database()
    doc = await db[ARTISANS_COLLECTION].find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil artisan introuvable")
    return _artisan_to_response(doc)


async def update_artisan(user_id: str, data: UpdateArtisanRequest) -> ArtisanResponse:
    db = get_database()
    doc = await db[ARTISANS_COLLECTION].find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil artisan introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        await db[ARTISANS_COLLECTION].update_one({"_id": doc["_id"]}, {"$set": update_fields})
    return await get_artisan(str(doc["_id"]))


async def update_artisan_by_id(artisan_id: str, data: UpdateArtisanRequest) -> ArtisanResponse:
    """(Admin) Mettre à jour le profil d'un artisan par son identifiant."""
    db = get_database()
    if not ObjectId.is_valid(artisan_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil artisan introuvable")
    doc = await db[ARTISANS_COLLECTION].find_one({"_id": ObjectId(artisan_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil artisan introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        await db[ARTISANS_COLLECTION].update_one({"_id": doc["_id"]}, {"$set": update_fields})
    return await get_artisan(artisan_id)


async def delete_artisan(user_id: str, is_admin: bool = False, target_artisan_id: Optional[str] = None) -> None:
    db = get_database()
    if target_artisan_id:
        if not ObjectId.is_valid(target_artisan_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil artisan introuvable")
        doc = await db[ARTISANS_COLLECTION].find_one({"_id": ObjectId(target_artisan_id)})
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil artisan introuvable")
        if doc["user_id"] != user_id and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que votre propre profil")
        await db[ARTISANS_COLLECTION].delete_one({"_id": ObjectId(target_artisan_id)})
        return

    result = await db[ARTISANS_COLLECTION].delete_one({"user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil artisan introuvable")


OFFICIAL_ARTISAN_NAME = "BurkinaSira"
_LEGACY_OFFICIAL_ARTISAN_NAME = "GoTours"


async def get_or_create_official_artisan(admin_user_id: str) -> ArtisanResponse:
    """Profil artisan officiel utilisé pour les produits ajoutés directement par l'admin,
    sans artisan associé (vitrine BurkinaSira)."""
    db = get_database()
    doc = await db[ARTISANS_COLLECTION].find_one(
        {"display_name": {"$in": [OFFICIAL_ARTISAN_NAME, _LEGACY_OFFICIAL_ARTISAN_NAME]}, "user_id": admin_user_id}
    )
    if doc:
        if doc["display_name"] != OFFICIAL_ARTISAN_NAME:
            await db[ARTISANS_COLLECTION].update_one(
                {"_id": doc["_id"]}, {"$set": {"display_name": OFFICIAL_ARTISAN_NAME}}
            )
            doc["display_name"] = OFFICIAL_ARTISAN_NAME
        return _artisan_to_response(doc)

    now = datetime.utcnow()
    doc = {
        "user_id": admin_user_id,
        "display_name": OFFICIAL_ARTISAN_NAME,
        "story": "Produits proposés directement par la plateforme BurkinaSira.",
        "photo_url": None,
        "region": "Centre",
        "city": None,
        "is_verified": True,
        "status": ArtisanStatus.ACTIVE.value,
        "average_rating": 0.0,
        "review_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    result = await db[ARTISANS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _artisan_to_response(doc)


async def set_verification_status(artisan_id: str, is_verified: bool) -> ArtisanResponse:
    db = get_database()
    if not ObjectId.is_valid(artisan_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artisan introuvable")
    result = await db[ARTISANS_COLLECTION].update_one(
        {"_id": ObjectId(artisan_id)},
        {"$set": {"is_verified": is_verified, "status": ArtisanStatus.ACTIVE.value, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artisan introuvable")
    return await get_artisan(artisan_id)


# --- Produits ---

def _product_to_summary(doc: dict) -> ProductSummary:
    return ProductSummary(
        id=str(doc["_id"]),
        artisan_id=doc["artisan_id"],
        name=doc["name"],
        slug=doc["slug"],
        category=doc["category"],
        price=doc["price"],
        currency=doc.get("currency", "XOF"),
        photo=doc["photos"][0] if doc.get("photos") else None,
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
        in_stock=doc.get("stock_quantity", 0) > 0,
        stock_quantity=doc.get("stock_quantity", 0),
    )


def _product_to_detail(doc: dict) -> ProductDetail:
    return ProductDetail(
        id=str(doc["_id"]),
        artisan_id=doc["artisan_id"],
        name=doc["name"],
        slug=doc["slug"],
        description=doc["description"],
        category=doc["category"],
        price=doc["price"],
        currency=doc.get("currency", "XOF"),
        photos=doc.get("photos", []),
        videos=doc.get("videos", []),
        stock_quantity=doc.get("stock_quantity", 0),
        fulfillment_mode=doc.get("fulfillment_mode", "les_deux"),
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
        status=doc.get("status", ProductStatus.DRAFT.value),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_product(data: CreateProductRequest, artisan_id: str) -> ProductDetail:
    db = get_database()
    await ensure_slug_index(db, PRODUCTS_COLLECTION)
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["artisan_id"] = artisan_id
    doc["slug"] = await generate_unique_slug(db, PRODUCTS_COLLECTION, data.name)
    doc["average_rating"] = 0.0
    doc["review_count"] = 0
    doc["status"] = ProductStatus.PUBLISHED.value
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[PRODUCTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _product_to_detail(doc)


async def list_products(
    category: Optional[ProductCategory] = None,
    artisan_id: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> ProductListResponse:
    db = get_database()
    query: dict = {"status": ProductStatus.PUBLISHED.value}
    if category:
        query["category"] = category.value if isinstance(category, ProductCategory) else category
    if artisan_id:
        query["artisan_id"] = artisan_id
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]

    total = await db[PRODUCTS_COLLECTION].count_documents(query)
    skip = (page - 1) * page_size
    docs = await db[PRODUCTS_COLLECTION].find(query).skip(skip).limit(page_size).to_list(length=page_size)

    return ProductListResponse(
        items=[_product_to_summary(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def list_my_products(artisan_id: str) -> list:
    db = get_database()
    docs = await db[PRODUCTS_COLLECTION].find({"artisan_id": artisan_id}).to_list(length=None)
    return [_product_to_detail(d) for d in docs]


async def get_product(product_id: str) -> ProductDetail:
    db = get_database()
    doc = await find_by_slug_or_id(db, PRODUCTS_COLLECTION, product_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produit introuvable")
    return _product_to_detail(doc)


async def update_product(
    product_id: str, data: UpdateProductRequest, current_artisan_id: Optional[str], is_admin: bool = False
) -> ProductDetail:
    db = get_database()
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produit introuvable")
    doc = await db[PRODUCTS_COLLECTION].find_one({"_id": ObjectId(product_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produit introuvable")
    if not is_admin and doc["artisan_id"] != current_artisan_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez modifier que vos propres produits")

    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        await db[PRODUCTS_COLLECTION].update_one({"_id": ObjectId(product_id)}, {"$set": update_fields})

    return await get_product(product_id)


async def delete_product(product_id: str, current_artisan_id: Optional[str], is_admin: bool = False) -> None:
    db = get_database()
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produit introuvable")
    doc = await db[PRODUCTS_COLLECTION].find_one({"_id": ObjectId(product_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produit introuvable")
    if not is_admin and doc["artisan_id"] != current_artisan_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez supprimer que vos propres produits")
    await db[PRODUCTS_COLLECTION].delete_one({"_id": ObjectId(product_id)})


# --- Commandes ---

def _order_to_response(doc: dict) -> OrderResponse:
    subtotal = doc.get("subtotal", doc["unit_price"] * doc["quantity"])
    delivery_fee = doc.get("delivery_fee", 0.0)
    history = [
        OrderStatusEvent(
            status=ev["status"],
            at=ev["at"],
            by=ev.get("by"),
            note=ev.get("note"),
        )
        for ev in doc.get("status_history", [])
    ]
    return OrderResponse(
        id=str(doc["_id"]),
        buyer_id=doc["buyer_id"],
        product_id=doc["product_id"],
        quantity=doc["quantity"],
        unit_price=doc["unit_price"],
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        delivery_region=doc.get("delivery_region"),
        delivery_address=doc.get("delivery_address"),
        agency_id=doc.get("agency_id"),
        delivery_provider=doc.get("delivery_provider"),
        delivery_eta_days_min=doc.get("delivery_eta_days_min"),
        delivery_eta_days_max=doc.get("delivery_eta_days_max"),
        tracking_number=doc.get("tracking_number"),
        carrier_note=doc.get("carrier_note"),
        estimated_delivery_date=doc.get("estimated_delivery_date"),
        settlement_status=doc.get("settlement_status"),
        total_price=doc["total_price"],
        currency=doc["currency"],
        fulfillment_mode=doc["fulfillment_mode"],
        status=doc.get("status", ArtisanOrderStatus.PENDING.value),
        status_history=history,
        created_at=doc["created_at"],
        updated_at=doc.get("updated_at"),
    )


async def create_order(data: CreateOrderRequest, buyer_id: str) -> OrderResponse:
    product = await get_product(data.product_id)
    if product.status != ProductStatus.PUBLISHED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce produit n'est pas disponible à la vente")
    if product.stock_quantity < data.quantity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stock insuffisant")

    mode = data.fulfillment_mode
    mode_value = mode.value if isinstance(mode, FulfillmentMode) else mode
    # Une commande doit choisir un mode concret : « les_deux » est ambigu
    # (retrait ou livraison ?) et contournerait le calcul des frais.
    if mode_value not in (FulfillmentMode.LIVRAISON.value, FulfillmentMode.RETRAIT.value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le mode de commande doit être « livraison » ou « retrait »",
        )
    if product.fulfillment_mode not in (mode_value, FulfillmentMode.LES_DEUX.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce mode de retrait/livraison n'est pas proposé pour ce produit",
        )

    subtotal = product.price * data.quantity

    # Frais de livraison auto-calculés (agence de livraison) uniquement en mode livraison.
    delivery_fee = 0.0
    delivery_region = None
    agency_id = None
    delivery_provider = None
    eta_min = None
    eta_max = None
    settlement_status = DeliverySettlementStatus.NOT_APPLICABLE.value
    if mode_value == FulfillmentMode.LIVRAISON.value:
        quote = await delivery_fee_service.compute_delivery_fee(data.delivery_region, subtotal)
        delivery_fee = quote.delivery_fee
        delivery_region = quote.region
        agency_id = quote.agency_id
        delivery_provider = quote.delivery_provider
        eta_min = quote.eta_days_min
        eta_max = quote.eta_days_max
        settlement_status = (
            DeliverySettlementStatus.PENDING.value
            if delivery_fee > 0
            else DeliverySettlementStatus.NOT_APPLICABLE.value
        )

    db = get_database()
    now = datetime.utcnow()
    doc = {
        "buyer_id": buyer_id,
        "product_id": product.id,
        "artisan_id": product.artisan_id,
        "quantity": data.quantity,
        "unit_price": product.price,
        "subtotal": round(subtotal, 2),
        "delivery_fee": delivery_fee,
        "delivery_region": delivery_region,
        "delivery_address": data.delivery_address,
        "agency_id": agency_id,
        "delivery_provider": delivery_provider,
        "delivery_eta_days_min": eta_min,
        "delivery_eta_days_max": eta_max,
        "tracking_number": None,
        "carrier_note": None,
        "estimated_delivery_date": None,
        "settlement_status": settlement_status,
        "settled_at": None,
        "settlement_id": None,
        "stock_restored": False,
        "total_price": round(subtotal + delivery_fee, 2),
        "currency": product.currency,
        "fulfillment_mode": mode_value,
        "status": ArtisanOrderStatus.PENDING.value,
        "status_history": [{"status": ArtisanOrderStatus.PENDING.value, "at": now, "by": buyer_id, "note": None}],
        "created_at": now,
        "updated_at": now,
    }
    result = await db[ORDERS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    await db[PRODUCTS_COLLECTION].update_one(
        {"_id": ObjectId(product.id)},
        {"$inc": {"stock_quantity": -data.quantity}},
    )

    return _order_to_response(doc)


async def list_my_orders(buyer_id: str) -> list:
    db = get_database()
    docs = await db[ORDERS_COLLECTION].find({"buyer_id": buyer_id}).sort("created_at", -1).to_list(length=None)
    return [_order_to_response(d) for d in docs]


async def _get_order_doc(order_id: str) -> dict:
    db = get_database()
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable")
    doc = await db[ORDERS_COLLECTION].find_one({"_id": ObjectId(order_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable")
    return doc


async def get_order(order_id: str, requester_id: Optional[str] = None, is_staff: bool = False) -> OrderResponse:
    doc = await _get_order_doc(order_id)
    if not is_staff and requester_id is not None and doc["buyer_id"] != requester_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé à cette commande")
    return _order_to_response(doc)


async def list_orders(
    status_filter: Optional[str] = None,
    agency_id: Optional[str] = None,
    artisan_id: Optional[str] = None,
    settlement_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> list:
    db = get_database()
    query: dict = {}
    if status_filter:
        query["status"] = status_filter
    if agency_id:
        query["agency_id"] = agency_id
    if artisan_id:
        query["artisan_id"] = artisan_id
    if settlement_status:
        query["settlement_status"] = settlement_status
    skip = (page - 1) * page_size
    docs = (
        await db[ORDERS_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(page_size)
        .to_list(length=page_size)
    )
    return [_order_to_response(d) for d in docs]


async def update_order_status(
    order_id: str, data: UpdateOrderStatusRequest, actor_id: str
) -> OrderResponse:
    db = get_database()
    doc = await _get_order_doc(order_id)
    current = doc.get("status", ArtisanOrderStatus.PENDING.value)
    new_status = data.status.value if isinstance(data.status, ArtisanOrderStatus) else data.status

    if new_status == current:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La commande a déjà ce statut")
    allowed = ARTISAN_ORDER_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transition invalide : {current} → {new_status}",
        )

    now = datetime.utcnow()
    set_fields: dict = {"status": new_status, "updated_at": now}
    if data.tracking_number is not None:
        set_fields["tracking_number"] = data.tracking_number
    if data.carrier_note is not None:
        set_fields["carrier_note"] = data.carrier_note
    if data.estimated_delivery_date is not None:
        set_fields["estimated_delivery_date"] = data.estimated_delivery_date

    # Restitution du stock une seule fois pour annulation / retour.
    if new_status in ARTISAN_ORDER_STOCK_RESTORING and not doc.get("stock_restored"):
        set_fields["stock_restored"] = True
        if ObjectId.is_valid(doc["product_id"]):
            await db[PRODUCTS_COLLECTION].update_one(
                {"_id": ObjectId(doc["product_id"])},
                {"$inc": {"stock_quantity": doc["quantity"]}},
            )
        # Une commande annulée/retournée ne doit plus être due à l'agence.
        if doc.get("settlement_status") == DeliverySettlementStatus.PENDING.value:
            set_fields["settlement_status"] = DeliverySettlementStatus.NOT_APPLICABLE.value

    event = {"status": new_status, "at": now, "by": actor_id, "note": data.note}
    await db[ORDERS_COLLECTION].update_one(
        {"_id": doc["_id"]},
        {"$set": set_fields, "$push": {"status_history": event}},
    )
    return await get_order(order_id, is_staff=True)
