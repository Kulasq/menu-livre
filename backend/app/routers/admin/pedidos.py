from __future__ import annotations
import asyncio
import json
from datetime import date
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Annotated

from app.database import get_db
from app.deps import get_current_admin, validar_token_query
from app.schemas.pedido import PedidoResponse, PedidoStatusUpdate, PedidoPagamentoUpdate, PedidoAdminCreate, PedidoAdminResponse
from app.services import pedido_service
from app.services import pedido_pubsub

router = APIRouter(prefix="/api/admin/pedidos", tags=["admin-pedidos"])


@router.get("/stream")
async def stream_pedidos(_usuario=Depends(validar_token_query)):
    """
    Server-Sent Events — push em tempo real de novos pedidos para o admin.

    Autenticação via query string (?token=...) porque EventSource não suporta
    headers customizados. Usar apenas o access token (15min), nunca o refresh.
    A validação é feita pela dependency validar_token_query (deps.py), que
    participa do sistema de DI do FastAPI — overrides de teste funcionam.

    Eventos emitidos:
      - connected: confirmação de conexão (o frontend faz um poll de catch-up)
      - novo-pedido: payload JSON com {id, numero, total, tipo, criado_em}
      - keepalive (comment ":" a cada 25s): mantém a conexão viva no Nginx

    A reconexão automática é gerenciada pelo EventSource nativo do browser
    (RFC 6202 — backoff exponencial por padrão).

    Problemas em produção a vigiar:
      - Nginx precisa de proxy_buffering off + proxy_read_timeout 3600s no path
        /api/admin/pedidos/stream (ver deploy/docker/nginx.conf)
      - Funciona apenas com single-worker uvicorn (pubsub em memória)
    """

    async def _gerar():
        q = pedido_pubsub.subscribe()
        try:
            # Evento inicial: avisa o frontend que a conexão está ativa
            # O frontend faz um poll HTTP para buscar pedidos que chegaram
            # durante o período de desconexão/reconexão (catch-up).
            yield "event: connected\ndata: {}\n\n"

            while True:
                try:
                    # Aguarda próximo pedido com timeout de keepalive
                    msg = await asyncio.wait_for(q.get(), timeout=25.0)
                    yield f"event: novo-pedido\ndata: {json.dumps(msg)}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive — impede que Nginx/proxies intermediários fechem
                    # a conexão por inatividade (comment SSE, não dispara eventos)
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            # Cliente desconectou — cleanup no finally
            raise
        finally:
            pedido_pubsub.unsubscribe(q)

    return StreamingResponse(
        _gerar(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # desativa buffer do Nginx para SSE
            "Connection": "keep-alive",
        },
    )


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