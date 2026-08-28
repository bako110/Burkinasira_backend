from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.diaspora import DiasporaContentType
from app.schemas.auth import TokenPayload
from app.schemas.diaspora import (
    CreateDiasporaContentRequest,
    UpdateDiasporaContentRequest,
    DiasporaContentResponse,
    CreateMeetupRequest,
    MeetupResponse,
)
from app.services import diaspora_service

router = APIRouter(prefix="/diaspora", tags=["Diaspora et tourisme de retour"])


@router.get("/content", response_model=list)
async def list_content(
    type: Optional[DiasporaContentType] = None,
    region: Optional[str] = None,
    q: Optional[str] = Query(default=None, description="Recherche texte"),
):
    """Circuits culturels, patrimoine familial, services pour visiteurs de retour (§31)."""
    return await diaspora_service.list_content(type=type, region=region, q=q)


@router.get("/content/{content_id}", response_model=DiasporaContentResponse)
async def get_content(content_id: str):
    """Détail d'un contenu diaspora."""
    return await diaspora_service.get_content(content_id)


@router.post("/content", response_model=DiasporaContentResponse, status_code=status.HTTP_201_CREATED)
async def create_content(
    data: CreateDiasporaContentRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Publier un contenu dédié à la diaspora."""
    return await diaspora_service.create_content(data, created_by=current_user.sub)


@router.patch("/content/{content_id}", response_model=DiasporaContentResponse)
async def update_content(
    content_id: str,
    data: UpdateDiasporaContentRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Mettre à jour un contenu diaspora."""
    return await diaspora_service.update_content(content_id, data)


@router.delete("/content/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(
    content_id: str,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN)),
):
    """(Admin) Supprimer un contenu diaspora."""
    await diaspora_service.delete_content(content_id)


@router.get("/meetups", response_model=list)
async def list_meetups(region: Optional[str] = None):
    """Rencontres communautaires proposées (§31)."""
    return await diaspora_service.list_meetups(region)


@router.post("/meetups", response_model=MeetupResponse, status_code=status.HTTP_201_CREATED)
async def create_meetup(
    data: CreateMeetupRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Organiser une rencontre communautaire."""
    return await diaspora_service.create_meetup(data, organizer_id=current_user.sub)


@router.post("/meetups/{meetup_id}/join", response_model=MeetupResponse)
async def join_meetup(meetup_id: str, current_user: TokenPayload = Depends(get_current_user)):
    """Participer à des rencontres communautaires."""
    return await diaspora_service.join_meetup(meetup_id, current_user.sub)
