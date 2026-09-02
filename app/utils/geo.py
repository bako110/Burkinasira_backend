"""Utilitaires de géolocalisation partagés.

Le filtrage « près de moi » se fait en mémoire (haversine) après la requête
Mongo. Suffisant pour des volumes modestes ; à migrer vers un index
géospatial 2dsphere si les collections grossissent.
"""
from math import asin, cos, radians, sin, sqrt
from typing import Optional

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en kilomètres entre deux points (latitude/longitude en degrés)."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return EARTH_RADIUS_KM * 2 * asin(sqrt(a))


def _extract_coords(doc: dict, *location_fields: str) -> Optional[tuple]:
    """Récupère (lat, lng) depuis le premier champ localisation présent et valide."""
    fields = location_fields or ("location",)
    for field in fields:
        loc = doc.get(field)
        if isinstance(loc, dict):
            lat = loc.get("latitude")
            lng = loc.get("longitude")
            if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
                return (lat, lng)
    return None


def filter_and_sort_by_distance(
    docs: list,
    near_lat: Optional[float],
    near_lng: Optional[float],
    radius_km: Optional[float],
    *location_fields: str,
) -> list:
    """Si near_lat/near_lng sont fournis :
      - écarte les documents sans coordonnées valides ;
      - écarte ceux au-delà de `radius_km` (si fourni) ;
      - trie les restants du plus proche au plus lointain.
    Sinon renvoie `docs` inchangé.
    """
    if near_lat is None or near_lng is None:
        return docs

    scored = []
    for d in docs:
        coords = _extract_coords(d, *location_fields)
        if coords is None:
            continue
        dist = haversine_km(near_lat, near_lng, coords[0], coords[1])
        if radius_km is not None and dist > radius_km:
            continue
        scored.append((dist, d))

    scored.sort(key=lambda x: x[0])
    return [d for _, d in scored]
