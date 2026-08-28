from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.artisan import ProductCategory, ArtisanStatus, ProductStatus
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
        region=doc["region"],
        city=doc.get("city"),
        is_verified=doc.get("is_verified", False),
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
    region: Optional[str] = None, verified_only: bool = False, include_all_statuses: bool = False
) -> list:
    db = get_database()
    query: dict = {} if include_all_statuses else {"status": ArtisanStatus.ACTIVE.value}
    if region:
        query["region"] = region
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


OFFICIAL_ARTISAN_NAME = "GoTours"


async def get_or_create_official_artisan(admin_user_id: str) -> ArtisanResponse:
    """Profil artisan officiel utilisé pour les produits ajoutés directement par l'admin,
    sans artisan associé (vitrine GoTours)."""
    db = get_database()
    doc = await db[ARTISANS_COLLECTION].find_one({"display_name": OFFICIAL_ARTISAN_NAME, "user_id": admin_user_id})
    if doc:
        return _artisan_to_response(doc)

    now = datetime.utcnow()
    doc = {
        "user_id": admin_user_id,
        "display_name": OFFICIAL_ARTISAN_NAME,
        "story": "Produits proposés directement par la plateforme GoTours.",
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
        category=doc["category"],
        price=doc["price"],
        currency=doc.get("currency", "XOF"),
        photo=doc["photos"][0] if doc.get("photos") else None,
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
        in_stock=doc.get("stock_quantity", 0) > 0,
    )


def _product_to_detail(doc: dict) -> ProductDetail:
    return ProductDetail(
        id=str(doc["_id"]),
        artisan_id=doc["artisan_id"],
        name=doc["name"],
        description=doc["description"],
        category=doc["category"],
        price=doc["price"],
        currency=doc.get("currency", "XOF"),
        photos=doc.get("photos", []),
        stock_quantity=doc.get("stock_quantity", 0),
        fulfillment_mode=doc.get("fulfillment_mode", "les_deux"),
        average_rating=doc.get("average_rating", 0.0),
        review_count=doc.get("review_count", 0),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_product(data: CreateProductRequest, artisan_id: str) -> ProductDetail:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["artisan_id"] = artisan_id
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


async def get_product(product_id: str) -> ProductDetail:
    db = get_database()
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produit introuvable")
    doc = await db[PRODUCTS_COLLECTION].find_one({"_id": ObjectId(product_id)})
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
    return OrderResponse(
        id=str(doc["_id"]),
        buyer_id=doc["buyer_id"],
        product_id=doc["product_id"],
        quantity=doc["quantity"],
        unit_price=doc["unit_price"],
        total_price=doc["total_price"],
        currency=doc["currency"],
        fulfillment_mode=doc["fulfillment_mode"],
        status=doc["status"],
        created_at=doc["created_at"],
    )


async def create_order(data: CreateOrderRequest, buyer_id: str) -> OrderResponse:
    product = await get_product(data.product_id)
    if product.stock_quantity < data.quantity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stock insuffisant")

    db = get_database()
    now = datetime.utcnow()
    doc = {
        "buyer_id": buyer_id,
        "product_id": data.product_id,
        "quantity": data.quantity,
        "unit_price": product.price,
        "total_price": product.price * data.quantity,
        "currency": product.currency,
        "fulfillment_mode": data.fulfillment_mode.value,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    result = await db[ORDERS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    await db[PRODUCTS_COLLECTION].update_one(
        {"_id": ObjectId(data.product_id)},
        {"$inc": {"stock_quantity": -data.quantity}},
    )

    return _order_to_response(doc)


async def list_my_orders(buyer_id: str) -> list:
    db = get_database()
    docs = await db[ORDERS_COLLECTION].find({"buyer_id": buyer_id}).sort("created_at", -1).to_list(length=None)
    return [_order_to_response(d) for d in docs]
