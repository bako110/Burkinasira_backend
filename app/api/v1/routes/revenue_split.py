from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.schemas.auth import TokenPayload
from app.schemas.revenue_split import (
    CreateRevenueSplitRuleRequest,
    RevenueSplitRuleResponse,
    RevenueSplitBreakdown,
)
from app.services import revenue_split_service, booking_service

router = APIRouter(prefix="/revenue-split", tags=["Où va mon argent ?"])


@router.get("/rules", response_model=list)
async def list_rules(current_user: TokenPayload = Depends(require_role(UserRole.ADMIN))):
    """(Admin) Règles de répartition contractuelle par type d'offre (§39)."""
    return await revenue_split_service.list_rules()


# Left ADMIN-only: revenue split rule configuration, a financial settlement setting.
@router.put("/rules", response_model=RevenueSplitRuleResponse)
async def set_rule(
    data: CreateRevenueSplitRuleRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Définir la règle de répartition pour un type d'offre."""
    return await revenue_split_service.set_rule(data)


@router.get("/bookings/{booking_id}", response_model=RevenueSplitBreakdown)
async def get_breakdown_for_booking(
    booking_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Consulter la répartition du prix payé pour une réservation compatible (§39)."""
    await booking_service.get_booking(booking_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN)
    return await revenue_split_service.get_breakdown_for_booking(booking_id)
