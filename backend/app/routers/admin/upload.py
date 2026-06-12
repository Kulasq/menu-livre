from __future__ import annotations

import os
import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image

from app.config import settings
from app.deps import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["admin-upload"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
# Formato real (detectado pelo Pillow) → extensão do arquivo salvo
EXTENSAO_POR_FORMATO = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


@router.post("/upload")
async def upload_imagem(
    file: UploadFile = File(...),
    _=Depends(get_current_admin),
):
    """Faz upload de imagem e retorna a URL pública."""
    # Gate rápido pelo content-type declarado — barato, mas é header do cliente
    # (falsificável); a validação real vem do Pillow logo abaixo.
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

    # Validação de conteúdo: o Pillow precisa decodificar a imagem de verdade.
    # Não confiar no content-type nem na extensão do nome enviado pelo cliente.
    try:
        Image.open(BytesIO(content)).verify()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Arquivo de imagem inválido ou corrompido.",
        )

    # verify() deixa a instância inutilizável — reabrir só para ler o formato real
    formato = (Image.open(BytesIO(content)).format or "").upper()
    if formato not in EXTENSAO_POR_FORMATO:
        raise HTTPException(
            status_code=400,
            detail="Formato de imagem não suportado. Use JPEG, PNG ou WebP.",
        )

    # Extensão derivada do formato real, nunca do file.filename (evita path/ext spoofing)
    filename = f"{uuid.uuid4().hex}.{EXTENSAO_POR_FORMATO[formato]}"

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(content)

    return {"url": f"/uploads/{filename}"}
