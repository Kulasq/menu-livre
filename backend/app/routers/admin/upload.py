from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import settings
from app.deps import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["admin-upload"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


@router.post("/upload")
async def upload_imagem(
    file: UploadFile = File(...),
    _=Depends(get_current_admin),
):
    """Faz upload de imagem e retorna a URL pública."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Tipo de arquivo não permitido. Use JPEG, PNG ou WebP.",
        )

    content = await file.read()

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Arquivo muito grande. Máximo: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    ext = "jpg"
    if file.filename and "." in file.filename:
        ext_raw = file.filename.rsplit(".", 1)[-1].lower()
        if ext_raw in ALLOWED_EXTENSIONS:
            ext = ext_raw

    filename = f"{uuid.uuid4().hex}.{ext}"

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    return {"url": f"/uploads/{filename}"}