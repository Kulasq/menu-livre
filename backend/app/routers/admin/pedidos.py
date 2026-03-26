from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Annotated

from app.database import get_db
from app.deps import get_current_admin
from app.schemas.pedido import PedidoResponse, PedidoStatusUpdate, PedidoPagamentoUpdate
from app.services import pedido_service

router = APIRouter(prefix="/api/admin/pedidos", tags=["admin-pedidos"])


@router.get("", response_model=list[PedidoResponse])
def listar_pedidos(
    status: Annotated[str | None, Query()] = None,
    tipo: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return pedido_service.listar_pedidos(db, status=status, tipo=tipo, page=page)


@router.get("/{pedido_id}", response_model=PedidoResponse)
def obter_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return pedido_service.obter_pedido(pedido_id, db)


@router.patch("/{pedido_id}/status", response_model=PedidoResponse)
def atualizar_status(
    pedido_id: int,
    dados: PedidoStatusUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return pedido_service.atualizar_status(pedido_id, dados, db)


@router.patch("/{pedido_id}/pagamento", response_model=PedidoResponse)
def atualizar_pagamento(
    pedido_id: int,
    dados: PedidoPagamentoUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return pedido_service.atualizar_pagamento(pedido_id, dados, db)