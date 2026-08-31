from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.core.security import require_role
from app.models.user import UserRole, UserStatus
from app.schemas.auth import TokenPayload
from app.schemas.admin import (
    NationalDashboardResponse,
    ChangeUserStatusRequest,
    ChangeUserRoleRequest,
    AdminUserSummary,
    SetCommissionRequest,
    CommissionResponse,
)
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["Administration FasoViva"])


@router.get("/dashboard", response_model=NationalDashboardResponse)
async def get_national_dashboard(current_user: TokenPayload = Depends(require_role(UserRole.ADMIN))):
    """Tableau de bord national (§43)."""
    return await admin_service.get_national_dashboard()


@router.get("/audit-log", response_model=list)
async def list_audit_log(
    limit: int = Query(default=100, le=500),
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """Journal d'audit des actions administratives sensibles."""
    return await admin_service.list_audit_log(limit)


@router.get("/users", response_model=list)
async def list_users(
    role: Optional[UserRole] = None,
    status_filter: Optional[UserStatus] = None,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """Gérer les utilisateurs et les professionnels."""
    return await admin_service.list_users(role, status_filter)


@router.patch("/users/{user_id}/status", response_model=AdminUserSummary)
async def change_user_status(
    user_id: str,
    data: ChangeUserStatusRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """Suspendre / réactiver un utilisateur."""
    return await admin_service.change_user_status(user_id, data, actor_id=current_user.sub)


@router.patch("/users/{user_id}/role", response_model=AdminUserSummary)
async def change_user_role(
    user_id: str,
    data: ChangeUserRoleRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """Changer le rôle d'un utilisateur."""
    return await admin_service.change_user_role(user_id, data, actor_id=current_user.sub)


@router.get("/commissions", response_model=list)
async def list_commissions(current_user: TokenPayload = Depends(require_role(UserRole.ADMIN))):
    """Gérer les commissions de la plateforme par type d'offre."""
    return await admin_service.list_commissions()


@router.put("/commissions", response_model=CommissionResponse)
async def set_commission(
    data: SetCommissionRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """Définir la commission pour un type d'offre."""
    return await admin_service.set_commission(data, actor_id=current_user.sub)
