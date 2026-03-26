from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_cliente
from app.schemas.cliente import ClienteIdentificar, ClienteUpdate, ClienteSessionResponse, ClienteResponse
from app.services import cliente_service

router = APIRouter(prefix="/api", tags=["clientes-publico"])


@router.post("/clientes/identificar", response_model=ClienteSessionResponse)
def identificar(dados: ClienteIdentificar, db: Session = Depends(get_db)):
    return cliente_service.identificar_cliente(dados, db)


@router.put("/clientes/{cliente_id}", response_model=ClienteResponse)
def atualizar(
    cliente_id: int,
    dados: ClienteUpdate,
    db: Session = Depends(get_db),
    cliente_atual=Depends(get_current_cliente),
):
    if cliente_atual.id != cliente_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Sem permissão")
    return cliente_service.atualizar_cliente(cliente_id, dados, db)