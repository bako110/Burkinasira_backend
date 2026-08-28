from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.models.offline import OfflinePackageType
from app.schemas.offline import (
    CreateOfflinePackageRequest,
    UpdateOfflinePackageRequest,
    OfflinePackageResponse,
    RegisterDownloadRequest,
    UserDownloadResponse,
)

PACKAGES_COLLECTION = "offline_packages"
DOWNLOADS_COLLECTION = "user_downloads"


def _package_to_response(doc: dict) -> OfflinePackageResponse:
    return OfflinePackageResponse(
        id=str(doc["_id"]),
        type=doc["type"],
        title=doc["title"],
        region=doc.get("region"),
        related_destination_id=doc.get("related_destination_id"),
        file_url=doc["file_url"],
        file_size_mb=doc.get("file_size_mb"),
        version=doc.get("version", 1),
        updated_at=doc["updated_at"],
    )


async def create_package(data: CreateOfflinePackageRequest) -> OfflinePackageResponse:
    db = get_database()
    now = datetime.utcnow()
    doc = data.model_dump()
    doc["version"] = 1
    doc["created_at"] = now
    doc["updated_at"] = now
    result = await db[PACKAGES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _package_to_response(doc)


async def list_packages(
    type: Optional[OfflinePackageType] = None,
    region: Optional[str] = None,
) -> list:
    db = get_database()
    query: dict = {}
    if type:
        query["type"] = type.value if isinstance(type, OfflinePackageType) else type
    if region:
        query["region"] = region
    docs = await db[PACKAGES_COLLECTION].find(query).to_list(length=None)
    return [_package_to_response(d) for d in docs]


async def get_package(package_id: str) -> OfflinePackageResponse:
    db = get_database()
    if not ObjectId.is_valid(package_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package introuvable")
    doc = await db[PACKAGES_COLLECTION].find_one({"_id": ObjectId(package_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package introuvable")
    return _package_to_response(doc)


async def update_package(package_id: str, data: UpdateOfflinePackageRequest) -> OfflinePackageResponse:
    db = get_database()
    if not ObjectId.is_valid(package_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package introuvable")

    update_fields = data.model_dump(exclude_unset=True, exclude_none=True, exclude={"bump_version"})
    update_fields["updated_at"] = datetime.utcnow()

    update_op: dict = {"$set": update_fields}
    if data.bump_version:
        update_op["$inc"] = {"version": 1}

    result = await db[PACKAGES_COLLECTION].update_one({"_id": ObjectId(package_id)}, update_op)
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package introuvable")
    return await get_package(package_id)


# --- Téléchargements utilisateur ---

async def register_download(data: RegisterDownloadRequest, user_id: str) -> UserDownloadResponse:
    package = await get_package(data.package_id)

    db = get_database()
    now = datetime.utcnow()
    await db[DOWNLOADS_COLLECTION].update_one(
        {"user_id": user_id, "package_id": data.package_id},
        {"$set": {"downloaded_version": package.version, "downloaded_at": now}},
        upsert=True,
    )
    return UserDownloadResponse(
        package_id=data.package_id, downloaded_version=package.version,
        downloaded_at=now, is_up_to_date=True,
    )


async def list_my_downloads(user_id: str) -> list:
    db = get_database()
    downloads = await db[DOWNLOADS_COLLECTION].find({"user_id": user_id}).to_list(length=None)

    results = []
    for d in downloads:
        package_doc = await db[PACKAGES_COLLECTION].find_one({"_id": ObjectId(d["package_id"])}) if ObjectId.is_valid(d["package_id"]) else None
        current_version = package_doc.get("version", 1) if package_doc else d["downloaded_version"]
        results.append(UserDownloadResponse(
            package_id=d["package_id"],
            downloaded_version=d["downloaded_version"],
            downloaded_at=d["downloaded_at"],
            is_up_to_date=d["downloaded_version"] >= current_version,
        ))
    return results
