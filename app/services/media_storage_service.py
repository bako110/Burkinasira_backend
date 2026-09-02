import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
ALLOWED_DOCUMENT_TYPES = {"application/pdf"}
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 Mo

# Redimensionnement/compression appliqués à l'upload : une photo de smartphone
# (souvent 3000-4000px de large, 3-8 Mo) est ramenée à une taille raisonnable pour
# l'affichage web, ce qui réduit fortement le temps de chargement côté client.
MAX_IMAGE_DIMENSION = 1600  # px, sur le plus grand côté
IMAGE_JPEG_QUALITY = 82
# Le GIF n'est pas ré-encodé (perte d'animation) — seuls JPEG/PNG/WEBP sont compressés.
COMPRESSIBLE_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "application/pdf": ".pdf",
}

UPLOAD_ROOT = Path(settings.UPLOAD_DIR)


async def upload_media(file: UploadFile, folder: str = "fasoviva") -> dict:
    """Enregistre une image ou une vidéo sur le disque du serveur et retourne son URL publique."""
    content_type = file.content_type or ""
    is_image = content_type in ALLOWED_IMAGE_TYPES
    is_video = content_type in ALLOWED_VIDEO_TYPES
    is_document = content_type in ALLOWED_DOCUMENT_TYPES

    if not is_image and not is_video and not is_document:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format de fichier non supporté (images JPEG/PNG/WEBP/GIF, vidéos MP4/MOV/WEBM ou documents PDF uniquement)",
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

    width = height = duration = None
    if is_image and content_type in COMPRESSIBLE_IMAGE_TYPES:
        contents, content_type, width, height = _compress_image(contents, content_type)
    elif is_image:
        width, height = _read_image_dimensions(contents)

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

    public_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/uploads/{safe_folder}/{filename}"

    if is_video:
        resource_type = "video"
    elif is_document:
        resource_type = "document"
    else:
        resource_type = "image"

    return {
        "url": public_url,
        "resource_type": resource_type,
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


def _compress_image(contents: bytes, content_type: str) -> tuple:
    """Redimensionne (si besoin) et recompresse une image pour réduire son poids
    avant stockage. Retourne (contenu, content_type, width, height). En cas
    d'échec (image corrompue, format inattendu...), renvoie le fichier original
    tel quel plutôt que de faire échouer tout l'upload."""
    import io

    from PIL import Image

    try:
        with Image.open(io.BytesIO(contents)) as img:
            img_format = img.format  # ex: "JPEG", "PNG", "WEBP"
            if img.mode in ("RGBA", "P") and img_format == "JPEG":
                img = img.convert("RGB")

            if max(img.width, img.height) > MAX_IMAGE_DIMENSION:
                img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.LANCZOS)

            buffer = io.BytesIO()
            save_kwargs = {}
            if img_format == "JPEG":
                save_kwargs = {"quality": IMAGE_JPEG_QUALITY, "optimize": True, "progressive": True}
            elif img_format == "WEBP":
                save_kwargs = {"quality": IMAGE_JPEG_QUALITY}
            elif img_format == "PNG":
                save_kwargs = {"optimize": True}
            img.save(buffer, format=img_format, **save_kwargs)

            compressed = buffer.getvalue()
            # Garde-fou : si la "compression" a paradoxalement grossi le fichier
            # (rare, mais possible sur de petites images déjà optimisées), on
            # garde l'original.
            if len(compressed) >= len(contents):
                return contents, content_type, img.width, img.height
            return compressed, content_type, img.width, img.height
    except Exception:
        width, height = _read_image_dimensions(contents)
        return contents, content_type, width, height
