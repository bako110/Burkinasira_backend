import secrets
from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException, status
from app.core.database import get_database
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import UserRole, UserStatus
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UpdateProfileRequest,
    UserPublic,
    UserVerification,
    TokenResponse,
)

COLLECTION = "users"

_card_token_index_ensured = False


async def _ensure_card_token_index(db) -> None:
    global _card_token_index_ensured
    if _card_token_index_ensured:
        return
    await db[COLLECTION].create_index("card_token", unique=True, sparse=True)
    _card_token_index_ensured = True


def _to_public(doc: dict) -> UserPublic:
    return UserPublic(
        id=str(doc["_id"]),
        full_name=doc["full_name"],
        email=doc["email"],
        phone=doc.get("phone"),
        role=doc["role"],
        is_verified=doc.get("is_verified", False),
        avatar_url=doc.get("avatar_url"),
        preferred_language=doc.get("preferred_language", "fr"),
        created_at=doc["created_at"],
    )


async def create_managed_user(email: str, password: str, full_name: str, role: UserRole) -> UserPublic:
    """Crée un compte utilisateur pour un membre d'équipe invité par un provider
    (ex: gérant d'une succursale), avec un mot de passe temporaire défini par l'inviteur.
    Le compte est directement actif et vérifié : il hérite de la confiance du compte
    qui l'invite, il n'a pas besoin de repasser par la vérification de documents."""
    db = get_database()
    existing = await db[COLLECTION].find_one({"email": email.lower()})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un compte existe déjà avec cet email")

    now = datetime.utcnow()
    doc = {
        "full_name": full_name,
        "email": email.lower(),
        "phone": None,
        "hashed_password": hash_password(password),
        "role": role.value,
        "status": UserStatus.ACTIVE.value,
        "is_verified": True,
        "avatar_url": None,
        "preferred_language": "fr",
        "created_at": now,
        "updated_at": now,
        "last_login_at": None,
    }
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_public(doc)


async def register_user(data: RegisterRequest) -> TokenResponse:
    db = get_database()
    existing = await db[COLLECTION].find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte existe déjà avec cet email",
        )

    now = datetime.utcnow()
    doc = {
        "full_name": data.full_name,
        "email": data.email.lower(),
        "phone": data.phone,
        "hashed_password": hash_password(data.password),
        "role": data.role.value,
        "status": UserStatus.ACTIVE.value,
        "is_verified": False,
        "avatar_url": None,
        "preferred_language": "fr",
        "created_at": now,
        "updated_at": now,
        "last_login_at": now,
    }
    result = await db[COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    token, expires_at = create_access_token(
        user_id=str(doc["_id"]), email=doc["email"], role=data.role
    )
    return TokenResponse(access_token=token, expires_at=expires_at, user=_to_public(doc))


async def login_user(data: LoginRequest) -> TokenResponse:
    db = get_database()
    doc = await db[COLLECTION].find_one({"email": data.email.lower()})
    if not doc or not verify_password(data.password, doc["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    if doc.get("status") != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte est suspendu ou supprimé",
        )

    await db[COLLECTION].update_one(
        {"_id": doc["_id"]}, {"$set": {"last_login_at": datetime.utcnow()}}
    )

    token, expires_at = create_access_token(
        user_id=str(doc["_id"]), email=doc["email"], role=UserRole(doc["role"])
    )
    return TokenResponse(access_token=token, expires_at=expires_at, user=_to_public(doc))


async def get_user_by_id(user_id: str) -> UserPublic:
    db = get_database()
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(user_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    return _to_public(doc)


async def get_or_create_card_token(user_id: str) -> str:
    """Retourne le token opaque et non-devinable utilisé dans le QR code de la
    carte FasoViva de cet utilisateur, en le générant s'il n'existe pas encore.
    Ce token ne doit jamais permettre de retrouver ou d'énumérer l'ObjectId réel."""
    db = get_database()
    await _ensure_card_token_index(db)
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    doc = await db[COLLECTION].find_one({"_id": ObjectId(user_id)}, {"card_token": 1})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    if doc.get("card_token"):
        return doc["card_token"]

    token = secrets.token_urlsafe(24)
    await db[COLLECTION].update_one({"_id": ObjectId(user_id)}, {"$set": {"card_token": token}})
    return token


async def verify_user_card(card_token: str) -> UserVerification:
    """Vérification publique d'une carte FasoViva à partir de son QR code.
    N'expose aucune donnée sensible (pas d'email, pas de téléphone, pas d'ObjectId)."""
    db = get_database()
    doc = await db[COLLECTION].find_one({"card_token": card_token})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carte introuvable")
    return UserVerification(
        full_name=doc["full_name"],
        role=doc["role"],
        is_verified=doc.get("is_verified", False),
        avatar_url=doc.get("avatar_url"),
        member_since=doc["created_at"],
    )


async def update_profile(user_id: str, data: UpdateProfileRequest) -> UserPublic:
    db = get_database()
    update_fields = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        await db[COLLECTION].update_one({"_id": ObjectId(user_id)}, {"$set": update_fields})
    return await get_user_by_id(user_id)


async def change_password(user_id: str, current_password: str, new_password: str) -> None:
    db = get_database()
    doc = await db[COLLECTION].find_one({"_id": ObjectId(user_id)})
    if not doc or not verify_password(current_password, doc["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mot de passe actuel incorrect",
        )
    await db[COLLECTION].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"hashed_password": hash_password(new_password), "updated_at": datetime.utcnow()}},
    )


async def delete_account(user_id: str) -> None:
    db = get_database()
    await db[COLLECTION].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"status": UserStatus.DELETED.value, "updated_at": datetime.utcnow()}},
    )
