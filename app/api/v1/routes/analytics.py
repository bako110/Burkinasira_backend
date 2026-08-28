from fastapi import APIRouter, Depends, status
from app.core.security import require_role
from app.models.user import UserRole
from app.models.analytics import AnalyticsEventType
from app.schemas.auth import TokenPayload
from app.schemas.analytics import TouristAnalyticsSummary, ProAnalyticsSummary
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics tourisme"])


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
