from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Annotated

from app.database import get_db
from app.deps import get_current_admin
from app.schemas.pedido import PedidoResponse, PedidoStatusUpdate, PedidoPagamentoUpdate, PedidoAdminCreate, PedidoAdminResponse
from app.services import pedido_service

router = APIRouter(prefix="/api/admin/pedidos", tags=["admin-pedidos"])


@router.get("", response_model=list[PedidoResponse])
def listar_pedidos(
    status: Annotated[str | None, Query()] = None,
    tipo: Annotated[str | None, Query()] = None,
    data_inicio: Annotated[date | None, Query()] = None,
    data_fim: Annotated[date | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return pedido_service.listar_pedidos(
        db, status=status, tipo=tipo,
        data_inicio=data_inicio, data_fim=data_fim,
        page=page, page_size=page_size,
    )


@router.get("/contagem")
def contar_pedidos(
    status: Annotated[str | None, Query()] = None,
    tipo: Annotated[str | None, Query()] = None,
    data_inicio: Annotated[date | None, Query()] = None,
    data_fim: Annotated[date | None, Query()] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    total = pedido_service.contar_pedidos(db, status=status, tipo=tipo,
                                          data_inicio=data_inicio, data_fim=data_fim)
    return {"total": total}


@router.post("", response_model=PedidoAdminResponse, status_code=201)
def criar_pedido_admin(
    dados: PedidoAdminCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return pedido_service.criar_pedido_admin(dados, db)


@router.delete("", status_code=200)
def deletar_pedidos_periodo(
    periodo: Annotated[str, Query(pattern="^(hoje|semana)$")],
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    total = pedido_service.deletar_pedidos_periodo(periodo, db)
    return {"deletados": total, "periodo": periodo}


@router.delete("/{pedido_id}", status_code=204)
def deletar_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    pedido_service.deletar_pedido(pedido_id, db)


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