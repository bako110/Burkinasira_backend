"""Vérification des `id_token` Google (Sign in with Google).

On récupère les clés publiques de Google (JWKS), on met le jeu de clés en cache
~1 h, puis on vérifie localement la signature du JWT + les claims `aud` / `iss` /
`exp`. Aucun appel réseau par connexion une fois le JWKS en cache.
"""
import logging
import time
from typing import Optional

import httpx
from fastapi import HTTPException, status
from jose import jwt, JWTError

from app.core.config import settings

logger = logging.getLogger("google_auth")

_GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
_JWKS_TTL_SECONDS = 3600
_LEEWAY_SECONDS = 30  # tolérance d'horloge

_jwks_cache: Optional[dict] = None
_jwks_fetched_at: float = 0.0


async def _get_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    now = time.time()
    if _jwks_cache is not None and (now - _jwks_fetched_at) < _JWKS_TTL_SECONDS:
        return _jwks_cache
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(_GOOGLE_CERTS_URL)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = now
    return _jwks_cache


def _pick_key(jwks: dict, kid: str) -> Optional[dict]:
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


async def verify_google_id_token(id_token: str) -> dict:
    """Retourne les claims vérifiés du `id_token` Google, ou lève une HTTPException.

    Claims utiles renvoyés : `sub` (identifiant Google stable), `email`,
    `email_verified`, `name`, `picture`.
    """
    allowed_aud = settings.google_client_ids
    if not allowed_aud:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La connexion Google n'est pas configurée sur ce serveur",
        )

    # 1. En-tête : doit être un JWT signé RS256.
    try:
        header = jwt.get_unverified_header(id_token)
    except JWTError as exc:
        logger.warning("id_token Google : en-tête illisible (%s) — longueur=%d parts=%d",
                       exc, len(id_token or ""), (id_token or "").count(".") + 1)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton Google illisible")

    if header.get("alg") != "RS256":
        logger.warning("id_token Google : alg inattendu %r", header.get("alg"))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton Google : algorithme inattendu")

    # 2. Claims non vérifiés — pour un diagnostic clair avant la vérif crypto.
    try:
        unverified = jwt.get_unverified_claims(id_token)
    except JWTError:
        unverified = {}
    token_aud = unverified.get("aud")
    if token_aud is not None and token_aud not in allowed_aud:
        logger.warning(
            "id_token Google : aud=%r ne correspond à aucun GOOGLE_CLIENT_IDS=%r",
            token_aud, allowed_aud,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton Google émis pour une autre application",
        )

    # 3. Clé publique correspondante.
    kid = header.get("kid")
    jwks = await _get_jwks()
    key = _pick_key(jwks, kid)
    if key is None:
        global _jwks_fetched_at
        _jwks_fetched_at = 0.0  # force le refresh (rotation de clé)
        jwks = await _get_jwks()
        key = _pick_key(jwks, kid)
    if key is None:
        logger.warning("id_token Google : kid=%r absent du JWKS", kid)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clé de signature Google inconnue")

    # 4. Vérification signature + exp + aud.
    last_aud_error: Optional[Exception] = None
    for aud in allowed_aud:
        try:
            claims = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=aud,
                options={"verify_at_hash": False, "leeway": _LEEWAY_SECONDS},
            )
            break
        except jwt.ExpiredSignatureError:
            logger.warning("id_token Google : expiré (exp=%r)", unverified.get("exp"))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton Google expiré, réessayez")
        except JWTError as exc:
            last_aud_error = exc
            continue
    else:
        logger.warning("id_token Google : échec de vérification (%s) aud_token=%r", last_aud_error, token_aud)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton Google invalide")

    if claims.get("iss") not in _ISSUERS:
        logger.warning("id_token Google : iss inattendu %r", claims.get("iss"))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Émetteur du jeton Google inattendu")

    if not claims.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton Google sans identifiant")

    return claims
