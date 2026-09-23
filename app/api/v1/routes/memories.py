from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user, require_role
from app.models.user import UserRole
from app.models.memory import MemoryTargetType
from app.schemas.auth import TokenPayload
from app.schemas.memory import CreateMemoryRequest, MemoryResponse, MemoryListResponse, ModerateMemoryRequest
from app.services import memory_service

router = APIRouter(prefix="/memories", tags=["Souvenirs des voyageurs"])


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    data: CreateMemoryRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Laisser un souvenir (photo/vidéo) public sur une fiche du site. Aucune
    réservation préalable n'est requise : tout utilisateur connecté peut
    partager un souvenir, visible immédiatement par tous."""
    return await memory_service.create_memory(data, author_id=current_user.sub)


@router.get("/target/{target_type}/{target_id}", response_model=MemoryListResponse)
async def list_memories_for_target(
    target_type: MemoryTargetType,
    target_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=60),
):
    """Souvenirs publiés pour une cible donnée (destination, hôtel, restaurant...)."""
    return await memory_service.list_memories_for_target(target_type.value, target_id, page, page_size)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Supprimer son propre souvenir (ou n'importe lequel si admin)."""
    await memory_service.delete_memory(memory_id, current_user.sub, is_admin=current_user.role == UserRole.ADMIN)


@router.patch("/{memory_id}/moderate", response_model=MemoryResponse)
async def moderate_memory(
    memory_id: str,
    data: ModerateMemoryRequest,
    current_user: TokenPayload = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """(Admin) Masquer ou republier un souvenir signalé."""
    return await memory_service.moderate_memory(memory_id, data)
