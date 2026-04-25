from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_cliente
from app.schemas.pedido import PedidoCreate, PedidoResponse, NovoPedidoResponse
from app.services import pedido_service

router = APIRouter(prefix="/api", tags=["pedidos-publico"])


@router.post("/pedidos", response_model=NovoPedidoResponse)
def criar_pedido(
    dados: PedidoCreate,
    db: Session = Depends(get_db),
    cliente=Depends(get_current_cliente),
):
    return pedido_service.criar_pedido(dados, cliente.id, db)


@router.get("/pedidos", response_model=list[PedidoResponse])
def listar_pedidos_cliente(
    limite: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    cliente=Depends(get_current_cliente),
):
    return pedido_service.listar_pedidos_cliente(cliente.id, db, limite, offset)


@router.get("/pedidos/{pedido_id}", response_model=PedidoResponse)
def obter_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    cliente=Depends(get_current_cliente),
):
    pedido = pedido_service.obter_pedido(pedido_id, db)
    if pedido.cliente_id != cliente.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Sem permissão")
    return pedido