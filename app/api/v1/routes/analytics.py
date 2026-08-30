from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.security import require_role
from app.models.user import UserRole
from app.models.analytics import AnalyticsEventType
from app.schemas.auth import TokenPayload
from app.schemas.analytics import TouristAnalyticsSummary, ProAnalyticsSummary
from app.schemas.guide_analytics import GuideAnalyticsSummary
from app.services import analytics_service, guide_analytics_service
from app.services.booking_provider_resolver import resolve_owner_id

router = APIRouter(prefix="/analytics", tags=["Analytics tourisme"])

PROVIDER_ITEM_TYPES = {"hotel", "restaurant", "transport", "product"}


async def _assert_owns_item(item_type: str, item_id: str, user_id: str) -> None:
    """Vérifie que l'item appartient bien au provider connecté avant de lui exposer ses données."""
    owner_id = await resolve_owner_id(item_type, item_id)
    if owner_id is None or owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cet établissement ne vous appartient pas")


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def track_event(type: AnalyticsEventType, item_type: str = None, item_id: str = None, query: str = None):
    """Enregistrer un événement de recherche/consultation (utilisé pour le taux de conversion, §45)."""
    await analytics_service.track_event(type, item_type, item_id, query)
    return {"status": "tracked"}


@router.get("/tourism", response_model=TouristAnalyticsSummary)
async def get_tourist_analytics(current_user: TokenPayload = Depends(require_role(UserRole.ADMIN))):
    """(Admin) Destinations les + consultées, saisonnalité, budget moyen, conversion (§45)."""
    return await analytics_service.get_tourist_summary()


@router.get("/pro/me", response_model=ProAnalyticsSummary)
async def get_my_pro_analytics(current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN))):
    """(Provider) Statistiques de performance de son activité."""
    return await analytics_service.get_pro_summary(current_user.sub)


@router.get("/pro/me/timeseries", response_model=GuideAnalyticsSummary)
async def get_my_provider_timeseries(
    item_type: str = Query(..., description="hotel, restaurant, transport ou product"),
    item_id: str = Query(...),
    currency: str = Query(default="XOF"),
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Provider) Statistiques détaillées (clients/réservations/revenus, quotidien/mensuel/annuel)
    pour un établissement précis (hôtel, restaurant, transport ou produit) qu'il possède."""
    if item_type not in PROVIDER_ITEM_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type d'activité invalide")
    if current_user.role != UserRole.ADMIN:
        await _assert_owns_item(item_type, item_id, current_user.sub)
    return await guide_analytics_service.get_provider_analytics(item_type, item_id, currency)
