from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.roads import RoadServiceType
from app.schemas.auth import TokenPayload
from app.schemas.roads import (
    CreateRoadServiceRequest,
    UpdateRoadServiceRequest,
    RoadServiceDetail,
    RoadServiceListResponse,
    ReportBreakdownRequest,
    BreakdownReportResponse,
    AssignBreakdownRequest,
)
from app.services import roads_service

router = APIRouter(prefix="/roads", tags=["Services automobiles et routiers"])


@router.get("", response_model=RoadServiceListResponse)
async def list_road_services(
    type: Optional[RoadServiceType] = None,
    region: Optional[str] = None,
    near_lat: Optional[float] = None,
    near_lng: Optional[float] = None,
    radius_km: Optional[float] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Stations-service, garages, mécaniciens, dépannage... le plus proche (§12)."""
    return await roads_service.list_road_services(
        type=type, region=region, near_lat=near_lat, near_lng=near_lng,
        radius_km=radius_km, page=page, page_size=page_size,
    )


@router.get("/breakdowns/me", response_model=list)
async def list_my_breakdowns(current_user: TokenPayload = Depends(get_current_user)):
    """Suivre ses signalements de panne."""
    return await roads_service.list_my_breakdowns(current_user.sub)


@router.get("/{service_id}", response_model=RoadServiceDetail)
async def get_road_service(service_id: str):
    """Détail d'un service automobile/routier."""
    return await roads_service.get_road_service(service_id)


@router.post("", response_model=RoadServiceDetail, status_code=status.HTTP_201_CREATED)
async def create_road_service(
    data: CreateRoadServiceRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Provider/Admin) Référencer un service automobile ou routier."""
    return await roads_service.create_road_service(data)


@router.patch("/{service_id}", response_model=RoadServiceDetail)
async def update_road_service(
    service_id: str,
    data: UpdateRoadServiceRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    """(Provider/Admin) Mettre à jour un service."""
    return await roads_service.update_road_service(service_id, data)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_road_service(
    service_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un service."""
    await roads_service.delete_road_service(service_id)


@router.post("/breakdowns", response_model=BreakdownReportResponse, status_code=status.HTTP_201_CREATED)
async def report_breakdown(
    data: ReportBreakdownRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Signaler une panne (§12)."""
    return await roads_service.report_breakdown(data, reporter_id=current_user.sub)


@router.post("/breakdowns/{report_id}/assign", response_model=BreakdownReportResponse)
async def assign_breakdown(
    report_id: str,
    data: AssignBreakdownRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Assigner un signalement de panne à un service."""
    return await roads_service.assign_breakdown(report_id, data.service_id)
