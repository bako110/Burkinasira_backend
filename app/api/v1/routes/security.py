from typing import Optional
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, get_current_user_optional, require_role
from app.models.user import UserRole
from app.models.emergency import IncidentStatus
from app.schemas.auth import TokenPayload
from app.schemas.emergency import (
    ReportIncidentRequest,
    IncidentReportResponse,
    ModerateIncidentRequest,
    CreateSecurityAlertRequest,
    UpdateSecurityAlertRequest,
    SecurityAlertResponse,
)
from app.services import emergency_service

router = APIRouter(prefix="/security-alerts", tags=["Urgences et sécurité"])


@router.get("", response_model=list)
async def list_active_alerts(region: Optional[str] = None):
    """Alertes officielles géolocalisées sur zones/routes à risque (§10)."""
    return await emergency_service.list_active_alerts(region)


@router.post("", response_model=SecurityAlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    data: CreateSecurityAlertRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Publier une alerte de sécurité."""
    return await emergency_service.create_alert(data, published_by=current_user.sub)


@router.post("/incidents", response_model=IncidentReportResponse, status_code=status.HTTP_201_CREATED)
async def report_incident(
    data: ReportIncidentRequest,
    current_user: Optional[TokenPayload] = Depends(get_current_user_optional),
):
    """Signaler un incident (avec modération a posteriori) (§10)."""
    return await emergency_service.report_incident(data, reporter_id=current_user.sub if current_user else None)


@router.get("/incidents", response_model=list)
async def list_incidents(
    status_filter: Optional[IncidentStatus] = None,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin/Modérateur) Historique des incidents signalés."""
    return await emergency_service.list_incidents(status_filter)


@router.patch("/incidents/{incident_id}", response_model=IncidentReportResponse)
async def moderate_incident(
    incident_id: str,
    data: ModerateIncidentRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin/Modérateur) Modérer un signalement d'incident."""
    return await emergency_service.moderate_incident(incident_id, data, moderator_id=current_user.sub)


@router.patch("/{alert_id}", response_model=SecurityAlertResponse)
async def update_alert(
    alert_id: str,
    data: UpdateSecurityAlertRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour une alerte de sécurité."""
    return await emergency_service.update_alert(alert_id, data)


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer une alerte de sécurité."""
    await emergency_service.delete_alert(alert_id)
