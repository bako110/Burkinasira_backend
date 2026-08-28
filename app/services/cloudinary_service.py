import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status
from app.core.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 Mo


async def upload_media(file: UploadFile, folder: str = "gotours") -> dict:
    """Téléverse une image ou une vidéo vers Cloudinary et retourne son URL publique."""
    content_type = file.content_type or ""
    is_image = content_type in ALLOWED_IMAGE_TYPES
    is_video = content_type in ALLOWED_VIDEO_TYPES

    if not is_image and not is_video:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format de fichier non supporté (images JPEG/PNG/WEBP/GIF ou vidéos MP4/MOV/WEBM uniquement)",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Le fichier dépasse la taille maximale autorisée (15 Mo)",
        )

    try:
        result = cloudinary.uploader.upload(
            contents,
            folder=folder,
            resource_type="video" if is_video else "image",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Échec de l'envoi du fichier au service de stockage",
        ) from exc

    return {
        "url": result.get("secure_url"),
        "resource_type": result.get("resource_type"),
        "width": result.get("width"),
        "height": result.get("height"),
        "duration": result.get("duration"),
    }
