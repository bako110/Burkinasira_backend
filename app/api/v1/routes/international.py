from typing import Optional
from fastapi import APIRouter, Depends, status
from app.core.security import require_role
from app.models.user import UserRole
from app.models.international import FirstVisitGuideCategory
from app.schemas.auth import TokenPayload
from app.schemas.international import (
    CreateGuideEntryRequest,
    UpdateGuideEntryRequest,
    GuideEntryResponse,
    SupportedLanguageResponse,
)
from app.services import international_service

router = APIRouter(prefix="/international", tags=["Tourisme international"])


@router.get("/first-visit-guide", response_model=list)
async def list_guide_entries(
    category: Optional[FirstVisitGuideCategory] = None,
    language: str = "fr",
):
    """Guide de première visite : culture, usages, monnaie, formalités, santé, sécurité, transport (§32)."""
    return await international_service.list_guide_entries(category=category, language=language)


@router.post("/first-visit-guide", response_model=GuideEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_guide_entry(
    data: CreateGuideEntryRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Publier une entrée du guide de première visite."""
    return await international_service.create_guide_entry(data)


@router.patch("/first-visit-guide/{entry_id}", response_model=GuideEntryResponse)
async def update_guide_entry(
    entry_id: str,
    data: UpdateGuideEntryRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Mettre à jour une entrée du guide."""
    return await international_service.update_guide_entry(entry_id, data)


@router.delete("/first-visit-guide/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guide_entry(
    entry_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer une entrée du guide."""
    await international_service.delete_guide_entry(entry_id)


@router.get("/languages", response_model=list)
async def list_supported_languages():
    """Langues disponibles pour changer la langue de l'application (§32)."""
    return await international_service.list_supported_languages()


@router.patch("/languages/{code}", response_model=SupportedLanguageResponse)
async def set_language_active(
    code: str,
    is_active: bool,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Activer/désactiver une langue de l'application."""
    return await international_service.set_language_active(code, is_active)
