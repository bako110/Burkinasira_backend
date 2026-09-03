"""Vérification des `id_token` Google (Sign in with Google).

On récupère les clés publiques de Google (JWKS), on met le jeu de clés en cache
~1 h, puis on vérifie localement la signature du JWT + les claims `aud` / `iss` /
`exp`. Aucun appel réseau par connexion une fois le JWKS en cache.
"""
import time
from typing import Optional

import httpx
from fastapi import HTTPException, status
from jose import jwt, JWTError

from app.core.config import settings

_GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
_JWKS_TTL_SECONDS = 3600

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

    try:
        unverified_header = jwt.get_unverified_header(id_token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton Google invalide")

    kid = unverified_header.get("kid")
    jwks = await _get_jwks()
    key = _pick_key(jwks, kid)
    if key is None:
        # Le jeton peut référencer une clé récemment tournée : on force un refresh.
        global _jwks_fetched_at
        _jwks_fetched_at = 0.0
        jwks = await _get_jwks()
        key = _pick_key(jwks, kid)
    if key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton Google invalide")

    try:
        claims = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=allowed_aud,
            options={"verify_at_hash": False},
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton Google invalide ou expiré")

    if claims.get("iss") not in _ISSUERS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Émetteur du jeton Google inattendu")

    if not claims.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton Google sans identifiant")

    return claims
