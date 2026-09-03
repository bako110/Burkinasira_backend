from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import require_role
from app.models.user import UserRole
from app.schemas.auth import TokenPayload
from app.schemas.weather import (
    CreateWeatherSnapshotRequest,
    WeatherSnapshotResponse,
    CreateWeatherAlertRequest,
    UpdateWeatherAlertRequest,
    WeatherAlertResponse,
)
from app.services import weather_service

router = APIRouter(prefix="/weather", tags=["Météo, environnement et conditions de voyage"])


@router.get("/current", response_model=WeatherSnapshotResponse)
async def get_current_weather(region: str):
    """Météo actuelle pour une région (§24)."""
    result = await weather_service.get_current_weather(region)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune donnée météo pour cette région")
    return result


@router.get("/forecast", response_model=list)
async def get_forecast(region: str, days: int = 5):
    """Prévisions météo à plusieurs jours."""
    return await weather_service.get_forecast(region, days)


@router.post("/snapshots", response_model=WeatherSnapshotResponse, status_code=status.HTTP_201_CREATED)
async def create_snapshot(
    data: CreateWeatherSnapshotRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Publier un relevé/prévision météo (alimenté par intégration ou saisie manuelle)."""
    return await weather_service.create_snapshot(data)


@router.get("/alerts", response_model=list)
async def list_active_alerts(region: Optional[str] = None):
    """Alertes météo/environnementales actives (§24)."""
    return await weather_service.list_active_alerts(region)


@router.post("/alerts", response_model=WeatherAlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    data: CreateWeatherAlertRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Publier une alerte météo/environnementale."""
    return await weather_service.create_alert(data, published_by=current_user.sub)


@router.patch("/alerts/{alert_id}", response_model=WeatherAlertResponse)
async def update_alert(
    alert_id: str,
    data: UpdateWeatherAlertRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour une alerte météo/environnementale."""
    return await weather_service.update_alert(alert_id, data)


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer une alerte météo/environnementale."""
    await weather_service.delete_alert(alert_id)


@router.get("/seasonal-tips", response_model=list)
async def list_seasonal_tips(season: Optional[str] = None):
    """Conseils de préparation selon la saison (§24)."""
    return await weather_service.list_seasonal_tips(season)
