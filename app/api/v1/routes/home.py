from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.core.security import get_current_user_optional
from app.schemas.auth import TokenPayload
from app.schemas.home import HomeFeedResponse, GlobalSearchResponse
from app.services import home_service

router = APIRouter(prefix="/home", tags=["Accueil intelligent"])


@router.get("/feed", response_model=HomeFeedResponse)
async def get_home_feed(
    near_lat: Optional[float] = None,
    near_lng: Optional[float] = None,
    current_user: Optional[TokenPayload] = Depends(get_current_user_optional),
):
    """Accueil intelligent : suggestions, destinations populaires, événements à venir,
    services indispensables à proximité, mode voyage (§2)."""
    return await home_service.get_home_feed(
        user_id=current_user.sub if current_user else None,
        near_lat=near_lat, near_lng=near_lng,
    )


@router.get("/search", response_model=GlobalSearchResponse)
async def global_search(q: str = Query(..., min_length=1)):
    """Recherche globale multi-types : lieu, activité, hôtel, restaurant, pharmacie,
    hôpital, événement, guide, transport... (§2)."""
    return await home_service.global_search(q)
