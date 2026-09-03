from typing import Optional
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.offline import OfflinePackageType
from app.schemas.auth import TokenPayload
from app.schemas.offline import (
    CreateOfflinePackageRequest,
    UpdateOfflinePackageRequest,
    OfflinePackageResponse,
    RegisterDownloadRequest,
    UserDownloadResponse,
)
from app.services import offline_service

router = APIRouter(prefix="/offline", tags=["Mode hors connexion"])


@router.get("/packages", response_model=list)
async def list_packages(type: Optional[OfflinePackageType] = None, region: Optional[str] = None):
    """Cartes, guides culturels/audio, fiches touristiques téléchargeables (§42)."""
    return await offline_service.list_packages(type=type, region=region)


@router.get("/packages/{package_id}", response_model=OfflinePackageResponse)
async def get_package(package_id: str):
    """Détail d'un package téléchargeable."""
    return await offline_service.get_package(package_id)


@router.post("/packages", response_model=OfflinePackageResponse, status_code=status.HTTP_201_CREATED)
async def create_package(
    data: CreateOfflinePackageRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Publier un package hors-ligne."""
    return await offline_service.create_package(data)


@router.patch("/packages/{package_id}", response_model=OfflinePackageResponse)
async def update_package(
    package_id: str,
    data: UpdateOfflinePackageRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour un package (avec incrément de version optionnel)."""
    return await offline_service.update_package(package_id, data)


@router.post("/downloads", response_model=UserDownloadResponse, status_code=status.HTTP_201_CREATED)
async def register_download(
    data: RegisterDownloadRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Télécharger une carte, un guide ou une fiche pour un usage hors-ligne."""
    return await offline_service.register_download(data, current_user.sub)


@router.get("/downloads/me", response_model=list)
async def list_my_downloads(current_user: TokenPayload = Depends(get_current_user)):
    """Ses contenus téléchargés, avec statut à jour ou non."""
    return await offline_service.list_my_downloads(current_user.sub)
