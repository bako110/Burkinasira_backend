from datetime import datetime
from math import radians, cos, sin, asin, sqrt
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.utils.slug import generate_unique_slug, find_by_slug_or_id, ensure_slug_index
from app.models.finance import MoneyServiceType, MoneyServiceStatus
from app.schemas.finance import (
    CreateMoneyServiceRequest,
    UpdateMoneyServiceRequest,
    MoneyServiceSummary,
    MoneyServiceDetail,
    MoneyServiceListResponse,
    CurrencyConversionRequest,
    CurrencyConversionResponse,
    WalletResponse,
    WalletTransactionResponse,
)

COLLECTION = "money_service_points"
RATES_COLLECTION = "exchange_rates"
WALLETS_COLLECTION = "wallets"
WALLET_TX_COLLECTION = "wallet_transactions"


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def _to_summary(doc: dict) -> MoneyServiceSummary:
    return MoneyServiceSummary(
        id=str(doc["_id"]),
        name=doc["name"],
        slug=doc["slug"],
        type=doc["type"],
        operator=doc.get("operator"),
        region=doc["region"],
        province=doc.get("province"),
        city=doc.get("city"),
        location=doc["location"],
    )


def _to_detail(doc: dict) -> MoneyServiceDetail:
    return MoneyServiceDetail(
        id=str(doc["_id"]),
        name=doc["name"],
        slug=doc["slug"],
        type=doc["type"],
        operator=doc.get("operator"),
        region=doc["region"],
        province=doc.get("province"),
        city=doc.get("city"),
        location=doc["location"],
        address=doc.get("address"),
        opening_hours=doc.get("opening_hours", []),
        contact_phone=doc.get("contact_phone"),
        data_source=doc.get("data_source", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def create_money_service(data: CreateMoneyServiceRequest) -> MoneyServiceDetail:
    db = get_database()
    await ensure_slug_index(db, COLLECTION)
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["slug"] = await generate_unique_slug(db, COLLECTION, data.name)
    doc["status"] = MoneyServiceStatus.PUBLISHED.value
    doc["data_source"] = {"verified": False, "source": None, "last_updated_at": now}
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_detail(doc)


async def list_money_services(
    type: Optional[MoneyServiceType] = None,
    region: Optional[str] = None,
    province: Optional[str] = None,
    q: Optional[str] = None,
    near_lat: Optional[float] = None,
    near_lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    page: int = 1,
    page_size: int = 20,
) -> MoneyServiceListResponse:
    db = get_database()
    query: dict = {"status": MoneyServiceStatus.PUBLISHED.value}
    if type:
        query["type"] = type.value if isinstance(type, MoneyServiceType) else type
    if region:
        query["region"] = region
    if province:
        query["province"] = province
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"city": {"$regex": q, "$options": "i"}},
            {"address": {"$regex": q, "$options": "i"}},
        ]

    all_docs = await db[COLLECTION].find(query).to_list(length=None)

    if near_lat is not None and near_lng is not None:
        all_docs.sort(
            key=lambda d: _haversine_km(near_lat, near_lng, d["location"]["latitude"], d["location"]["longitude"])
        )
        if radius_km is not None:
            all_docs = [
                d for d in all_docs
                if _haversine_km(near_lat, near_lng, d["location"]["latitude"], d["location"]["longitude"]) <= radius_km
            ]

    total = len(all_docs)
    start = (page - 1) * page_size
    page_docs = all_docs[start:start + page_size]

    return MoneyServiceListResponse(
        items=[_to_summary(d) for d in page_docs],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_money_service(service_id: str) -> MoneyServiceDetail:
    db = get_database()
    doc = await find_by_slug_or_id(db, COLLECTION, service_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Point de service introuvable")
    return _to_detail(doc)


async def update_money_service(service_id: str, data: UpdateMoneyServiceRequest) -> MoneyServiceDetail:
    db = get_database()
    if not ObjectId.is_valid(service_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Point de service introuvable")
    update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db[COLLECTION].update_one({"_id": ObjectId(service_id)}, {"$set": update_fields})
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Point de service introuvable")
    return await get_money_service(service_id)


async def delete_money_service(service_id: str) -> None:
    db = get_database()
    if not ObjectId.is_valid(service_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Point de service introuvable")
    result = await db[COLLECTION].delete_one({"_id": ObjectId(service_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Point de service introuvable")


# --- Convertisseur de devises ---

async def convert_currency(data: CurrencyConversionRequest) -> CurrencyConversionResponse:
    db = get_database()
    rate_doc = await db[RATES_COLLECTION].find_one({
        "base_currency": data.from_currency,
        "target_currency": data.to_currency,
    })
    if not rate_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Taux de change {data.from_currency}->{data.to_currency} non disponible",
        )
    converted = data.amount * rate_doc["rate"]
    return CurrencyConversionResponse(
        amount=data.amount,
        from_currency=data.from_currency,
        to_currency=data.to_currency,
        rate=rate_doc["rate"],
        converted_amount=converted,
        rate_updated_at=rate_doc["updated_at"],
    )


async def set_exchange_rate(base_currency: str, target_currency: str, rate: float) -> None:
    db = get_database()
    await db[RATES_COLLECTION].update_one(
        {"base_currency": base_currency, "target_currency": target_currency},
        {"$set": {"rate": rate, "updated_at": datetime.utcnow()}},
        upsert=True,
    )


# --- Portefeuille (lecture seule au Lot 1 — paiement réel en Lot 2) ---

async def get_or_create_wallet(user_id: str) -> WalletResponse:
    db = get_database()
    doc = await db[WALLETS_COLLECTION].find_one({"user_id": user_id})
    if not doc:
        now = datetime.utcnow()
        new_doc = {"user_id": user_id, "balance": 0.0, "currency": "XOF", "created_at": now, "updated_at": now}
        result = await db[WALLETS_COLLECTION].insert_one(new_doc)
        new_doc["_id"] = result.inserted_id
        doc = new_doc
    return WalletResponse(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        balance=doc["balance"],
        currency=doc["currency"],
        updated_at=doc["updated_at"],
    )


async def list_wallet_transactions(user_id: str) -> list:
    db = get_database()
    docs = await db[WALLET_TX_COLLECTION].find({"user_id": user_id}).sort("created_at", -1).to_list(length=None)
    return [
        WalletTransactionResponse(
            id=str(d["_id"]),
            type=d["type"],
            amount=d["amount"],
            currency=d.get("currency", "XOF"),
            status=d["status"],
            description=d.get("description"),
            reference=d.get("reference"),
            created_at=d["created_at"],
        )
        for d in docs
    ]
