from fastapi import APIRouter, Depends, File, UploadFile
from app.core.security import get_current_user
from app.schemas.auth import TokenPayload
from app.schemas.media import MediaUploadResponse
from app.services import media_storage_service

router = APIRouter(prefix="/media", tags=["Médias"])


@router.post("/upload", response_model=MediaUploadResponse)
async def upload_media(
    file: UploadFile = File(...),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Téléverser une image ou une vidéo (ex. publication communautaire) et récupérer son URL publique."""
    return await media_storage_service.upload_media(file, folder=f"users/{current_user.sub}")
