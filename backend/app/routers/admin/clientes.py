from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated

from app.database import get_db
from app.deps import get_current_admin
from app.models.cliente import Cliente
from app.schemas.cliente import (
    ClienteResponse,
    ClienteAdminListResponse,
    ClienteAdminDetalhe,
    ClienteAdminUpdate,
    EnderecoCreate,
    EnderecoResponse,
)
from app.schemas.pedido import PedidoResponse
from app.services.cliente_service import (
    normalizar_telefone,
    listar_clientes_admin,
    listar_enderecos,
    atualizar_cliente_admin,
    deletar_cliente,
    criar_cliente_admin,
    adicionar_endereco_admin,
    deletar_endereco_admin,
)
from app.services.pedido_service import listar_pedidos_cliente

router = APIRouter(prefix="/api/admin/clientes", tags=["admin-clientes"])


@router.get("", response_model=list[ClienteResponse])
def buscar_clientes(
    telefone: Annotated[str | None, Query()] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Busca clientes por telefone (exato, normalizado). Retorna lista com 0 ou 1 item. Usado pelo PDV."""
    if not telefone:
        return []
    tel_normalizado = normalizar_telefone(telefone)
    cliente = db.query(Cliente).filter(Cliente.telefone == tel_normalizado).first()
    return [cliente] if cliente else []


@router.get("/lista", response_model=ClienteAdminListResponse)
def listar_clientes(
    q: Annotated[str | None, Query()] = None,
    segmento: Annotated[str | None, Query()] = None,
    ordenar: Annotated[str, Query()] = "ultimo_pedido",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 30,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Lista todos os clientes com filtros, ordenação e paginação para o painel admin."""
    clientes, total = listar_clientes_admin(
        db, q=q, segmento=segmento, ordenar=ordenar, page=page, page_size=page_size
    )
    return {"clientes": clientes, "total": total}


@router.post("", response_model=ClienteAdminDetalhe, status_code=201)
def criar_cliente(
    dados: ClienteAdminUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Cria um novo cliente diretamente pelo painel admin."""
    if not dados.nome:
        raise HTTPException(status_code=400, detail="Nome é obrigatório")
    if not dados.telefone:
        raise HTTPException(status_code=400, detail="Telefone é obrigatório")
    return criar_cliente_admin(dados.nome, dados.telefone, db)


@router.get("/{cliente_id}", response_model=ClienteAdminDetalhe)
def detalhe_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Retorna detalhes completos de um cliente."""
    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente


@router.put("/{cliente_id}", response_model=ClienteAdminDetalhe)
def atualizar_cliente(
    cliente_id: int,
    dados: ClienteAdminUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Atualiza nome e/ou telefone de um cliente."""
    return atualizar_cliente_admin(cliente_id, dados, db)


@router.delete("/{cliente_id}", status_code=204)
def excluir_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Remove um cliente e todos os seus endereços."""
    deletar_cliente(cliente_id, db)


@router.get("/{cliente_id}/pedidos", response_model=list[PedidoResponse])
def pedidos_do_cliente(
    cliente_id: int,
    limite: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Lista pedidos de um cliente específico."""
    if not db.get(Cliente, cliente_id):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return listar_pedidos_cliente(cliente_id, db, limite=limite, offset=offset)


@router.get("/{cliente_id}/enderecos", response_model=list[EnderecoResponse])
def enderecos_do_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Lista endereços salvos de um cliente."""
    if not db.get(Cliente, cliente_id):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return listar_enderecos(db, cliente_id)


@router.post("/{cliente_id}/enderecos", response_model=EnderecoResponse, status_code=201)
def adicionar_endereco(
    cliente_id: int,
    dados: EnderecoCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Adiciona um endereço a um cliente."""
    return adicionar_endereco_admin(cliente_id, dados.endereco, db)


@router.delete("/{cliente_id}/enderecos/{endereco_id}", status_code=204)
def excluir_endereco(
    cliente_id: int,
    endereco_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Remove um endereço de um cliente."""
    deletar_endereco_admin(endereco_id, cliente_id, db)
