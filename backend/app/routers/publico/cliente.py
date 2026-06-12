from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_cliente
from app.limiter import limiter
from app.schemas.cliente import (
    ClienteIdentificar,
    ClienteUpdate,
    ClienteSessionResponse,
    ClienteResponse,
    EnderecoResponse,
)
from app.services import cliente_service

router = APIRouter(prefix="/api", tags=["clientes-publico"])


@router.post("/clientes/identificar", response_model=ClienteSessionResponse)
@limiter.limit("10/minute")
def identificar(request: Request, dados: ClienteIdentificar, db: Session = Depends(get_db)):
    # Rate limited: endpoint público sem auth que retorna dados do cliente por
    # telefone — limite por IP evita enumeração em massa da base de clientes (LGPD).
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


@router.get("/clientes/{cliente_id}/enderecos", response_model=list[EnderecoResponse])
def listar_enderecos(
    cliente_id: int,
    db: Session = Depends(get_db),
    cliente_atual=Depends(get_current_cliente),
):
    from fastapi import HTTPException
    if cliente_atual.id != cliente_id:
        raise HTTPException(status_code=403, detail="Sem permissão")
    return cliente_service.listar_enderecos(db, cliente_id)


@router.delete("/clientes/enderecos/{endereco_id}", status_code=204)
def deletar_endereco(
    endereco_id: int,
    db: Session = Depends(get_db),
    cliente_atual=Depends(get_current_cliente),
):
    cliente_service.deletar_endereco(db, endereco_id, cliente_atual.id)