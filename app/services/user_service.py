import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from bson import ObjectId
from fastapi import BackgroundTasks, HTTPException, status
from app.core.config import settings
from app.core.database import get_database
from app.core.email import send_welcome_email, send_password_reset_email
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import UserRole, UserStatus
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    GoogleLoginRequest,
    UpdateProfileRequest,
    UserPublic,
    UserVerification,
    TokenResponse,
)

COLLECTION = "users"

_card_token_index_ensured = False
_google_sub_index_ensured = False


async def _ensure_card_token_index(db) -> None:
    global _card_token_index_ensured
    if _card_token_index_ensured:
        return
    await db[COLLECTION].create_index("card_token", unique=True, sparse=True)
    _card_token_index_ensured = True


async def _ensure_google_sub_index(db) -> None:
    global _google_sub_index_ensured
    if _google_sub_index_ensured:
        return
    await db[COLLECTION].create_index("google_sub", unique=True, sparse=True)
    _google_sub_index_ensured = True


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


async def register_user(data: RegisterRequest, background_tasks: Optional[BackgroundTasks] = None) -> TokenResponse:
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

    # Email de bienvenue en arrière-plan : son échec n'affecte pas l'inscription.
    if background_tasks is not None:
        background_tasks.add_task(send_welcome_email, doc["email"], doc["full_name"])

    token, expires_at = create_access_token(
        user_id=str(doc["_id"]), email=doc["email"], role=data.role
    )
    return TokenResponse(access_token=token, expires_at=expires_at, user=_to_public(doc))


# --- Réinitialisation de mot de passe ---

_RESET_TOKEN_TTL = timedelta(hours=1)
_reset_index_ensured = False


async def _ensure_reset_index(db) -> None:
    global _reset_index_ensured
    if _reset_index_ensured:
        return
    await db["password_reset_tokens"].create_index("token_hash", unique=True)
    await db["password_reset_tokens"].create_index("expires_at", expireAfterSeconds=0)
    _reset_index_ensured = True


def _hash_reset_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def request_password_reset(email: str, background_tasks: Optional[BackgroundTasks] = None) -> None:
    """Génère un token de reset et envoie l'email. Ne révèle jamais si l'email
    existe : la fonction retourne silencieusement dans tous les cas."""
    db = get_database()
    await _ensure_reset_index(db)

    doc = await db[COLLECTION].find_one({"email": (email or "").lower()})
    # Comptes Google-only (sans mot de passe) : pas de reset par email.
    if not doc or not doc.get("hashed_password"):
        return
    if doc.get("status") != UserStatus.ACTIVE.value:
        return

    raw_token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    await db["password_reset_tokens"].delete_many({"user_id": str(doc["_id"])})
    await db["password_reset_tokens"].insert_one({
        "user_id": str(doc["_id"]),
        "token_hash": _hash_reset_token(raw_token),
        "created_at": now,
        "expires_at": now + _RESET_TOKEN_TTL,
        "used_at": None,
    })

    reset_url = f"{settings.PUBLIC_WEB_URL.rstrip('/')}/reset-password?token={raw_token}"
    if background_tasks is not None:
        background_tasks.add_task(send_password_reset_email, doc["email"], doc["full_name"], reset_url)
    else:
        await send_password_reset_email(doc["email"], doc["full_name"], reset_url)


async def reset_password(raw_token: str, new_password: str) -> None:
    db = get_database()
    await _ensure_reset_index(db)

    entry = await db["password_reset_tokens"].find_one({"token_hash": _hash_reset_token(raw_token)})
    if not entry or entry.get("used_at") is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lien invalide ou déjà utilisé")
    if entry["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lien expiré, refaites une demande")

    if not ObjectId.is_valid(entry["user_id"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lien invalide")

    now = datetime.utcnow()
    await db[COLLECTION].update_one(
        {"_id": ObjectId(entry["user_id"])},
        {"$set": {"hashed_password": hash_password(new_password), "updated_at": now}},
    )
    await db["password_reset_tokens"].update_one({"_id": entry["_id"]}, {"$set": {"used_at": now}})


async def login_user(data: LoginRequest) -> TokenResponse:
    db = get_database()
    doc = await db[COLLECTION].find_one({"email": data.email.lower()})
    if not doc or not doc.get("hashed_password") or not verify_password(data.password, doc["hashed_password"]):
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


async def login_with_google(data: GoogleLoginRequest) -> TokenResponse:
    """Connexion / inscription via un `id_token` Google.

    Ordre de résolution du compte :
      1. compte déjà lié à ce `google_sub` ;
      2. sinon, compte existant avec le même email (on le lie à Google) ;
      3. sinon, création d'un nouveau compte sans mot de passe.
    """
    from app.services.google_auth_service import verify_google_id_token

    claims = await verify_google_id_token(data.id_token)
    google_sub = claims["sub"]
    email = (claims.get("email") or "").lower()
    email_verified = bool(claims.get("email_verified"))
    full_name = claims.get("name") or (email.split("@")[0] if email else "Utilisateur Google")
    avatar_url = claims.get("picture")

    db = get_database()
    await _ensure_google_sub_index(db)
    now = datetime.utcnow()

    doc = await db[COLLECTION].find_one({"google_sub": google_sub})

    if not doc and email:
        doc = await db[COLLECTION].find_one({"email": email})
        if doc:
            # On lie le compte email existant à Google.
            await db[COLLECTION].update_one(
                {"_id": doc["_id"]},
                {"$set": {"google_sub": google_sub, "updated_at": now,
                          **({"avatar_url": avatar_url} if avatar_url and not doc.get("avatar_url") else {})}},
            )
            doc["google_sub"] = google_sub

    is_new = False
    if not doc:
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le compte Google ne fournit pas d'adresse email",
            )
        is_new = True
        new_doc = {
            "full_name": full_name,
            "email": email,
            "phone": None,
            "hashed_password": None,
            "google_sub": google_sub,
            "auth_provider": "google",
            "email_verified": email_verified,  # email confirmé par Google
            "role": data.role.value,
            "role_chosen": data.role != UserRole.TOURIST,
            "status": UserStatus.ACTIVE.value,
            # Comme à l'inscription classique : is_verified concerne la
            # vérification de documents (guides/prestataires) et reste False.
            # Un compte Google guide/prestataire passe donc bien par /pro/pending.
            "is_verified": False,
            "avatar_url": avatar_url,
            "preferred_language": "fr",
            "created_at": now,
            "updated_at": now,
            "last_login_at": now,
        }
        result = await db[COLLECTION].insert_one(new_doc)
        new_doc["_id"] = result.inserted_id
        doc = new_doc
    else:
        if doc.get("status") != UserStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ce compte est suspendu ou supprimé",
            )
        updates: dict = {"last_login_at": now}
        # Choix du rôle en 2e temps (écran post-connexion Google) : autorisé une
        # seule fois, tant que le compte Google est encore "tourist" et que le
        # rôle n'a pas déjà été confirmé.
        if (
            data.role != UserRole.TOURIST
            and not doc.get("role_chosen")
            and doc.get("role") == UserRole.TOURIST.value
            and doc.get("auth_provider") == "google"
        ):
            updates["role"] = data.role.value
            updates["role_chosen"] = True
            doc["role"] = data.role.value
        await db[COLLECTION].update_one({"_id": doc["_id"]}, {"$set": updates})

    token, expires_at = create_access_token(
        user_id=str(doc["_id"]), email=doc["email"], role=UserRole(doc["role"])
    )
    return TokenResponse(
        access_token=token, expires_at=expires_at, user=_to_public(doc), is_new=is_new
    )


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
    carte BurkinaSira de cet utilisateur, en le générant s'il n'existe pas encore.
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
    """Vérification publique d'une carte BurkinaSira à partir de son QR code.
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
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    if not doc.get("hashed_password"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce compte utilise la connexion Google et n'a pas de mot de passe",
        )
    if not verify_password(current_password, doc["hashed_password"]):
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
