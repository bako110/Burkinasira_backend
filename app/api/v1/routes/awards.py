import re
from pathlib import Path

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/awards", tags=["Distinctions"])

_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
_EDITION_RE = re.compile(r"(20\d{2})")

AWARDS_TITLE = "Lauréat du SITHO"


@router.get("")
async def list_awards():
    """Photos des distinctions (SITHO 2025 et 2026).

    Il suffit de déposer les images dans `uploads/awards/` en commençant le nom
    par l'année de l'édition (ex. `2025-remise-prix.jpg`, `2026-equipe.webp`).
    """
    folder = Path(settings.UPLOAD_DIR) / "awards"
    items = []
    if folder.is_dir():
        for f in sorted(folder.iterdir()):
            if f.suffix.lower() not in _IMAGE_EXT:
                continue
            m = _EDITION_RE.match(f.stem)
            items.append({
                "id": f.stem,
                "edition": int(m.group(1)) if m else None,
                "url": f"/uploads/awards/{f.name}",
            })
    items.sort(key=lambda i: (-(i["edition"] or 0), i["id"]))
    return {"title": AWARDS_TITLE, "items": items}
