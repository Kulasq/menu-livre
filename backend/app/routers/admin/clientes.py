from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Annotated

from app.database import get_db
from app.deps import get_current_admin
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteResponse
from app.services.cliente_service import normalizar_telefone

router = APIRouter(prefix="/api/admin/clientes", tags=["admin-clientes"])


@router.get("", response_model=list[ClienteResponse])
def buscar_clientes(
    telefone: Annotated[str | None, Query()] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Busca clientes por telefone (exato, normalizado). Retorna lista com 0 ou 1 item."""
    if not telefone:
        return []
    tel_normalizado = normalizar_telefone(telefone)
    cliente = db.query(Cliente).filter(Cliente.telefone == tel_normalizado).first()
    return [cliente] if cliente else []
