import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 Mo

EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}

UPLOAD_ROOT = Path(settings.UPLOAD_DIR)


async def upload_media(file: UploadFile, folder: str = "gotours") -> dict:
    """Enregistre une image ou une vidéo sur le disque du serveur et retourne son URL publique."""
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

    safe_folder = folder.strip("/").replace("..", "")
    target_dir = UPLOAD_ROOT / safe_folder
    target_dir.mkdir(parents=True, exist_ok=True)

    extension = EXTENSION_BY_CONTENT_TYPE.get(content_type, "")
    filename = f"{uuid.uuid4().hex}{extension}"
    file_path = target_dir / filename

    try:
        file_path.write_bytes(contents)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Échec de l'enregistrement du fichier sur le serveur",
        ) from exc

    width = height = duration = None
    if is_image:
        width, height = _read_image_dimensions(contents)

    public_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/uploads/{safe_folder}/{filename}"

    return {
        "url": public_url,
        "resource_type": "video" if is_video else "image",
        "width": width,
        "height": height,
        "duration": duration,
    }


def _read_image_dimensions(contents: bytes) -> tuple:
    try:
        from PIL import Image
        import io

        with Image.open(io.BytesIO(contents)) as img:
            return img.width, img.height
    except Exception:
        return None, None
