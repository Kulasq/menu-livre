from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.cliente import Cliente
from app.schemas.cliente import ClienteIdentificar, ClienteUpdate
from app.services.auth_service import criar_token_cliente
import re


def normalizar_telefone(telefone: str) -> str:
    return re.sub(r"\D", "", telefone)


def identificar_cliente(dados: ClienteIdentificar, db: Session) -> dict:
    """Cria ou recupera cliente pelo telefone. Retorna cliente + token de sessão."""
    telefone = normalizar_telefone(dados.telefone)

    if len(telefone) < 10 or len(telefone) > 13:
        raise HTTPException(
            status_code=400,
            detail="Telefone inválido. Use o formato: 81 99999-9999",
        )

    cliente = db.query(Cliente).filter(Cliente.telefone == telefone).first()

    if cliente:
        # Cliente existente — atualiza nome se fornecido
        if dados.nome and dados.nome != cliente.nome:
            cliente.nome = dados.nome
            db.commit()
    else:
        # Novo cliente
        if not dados.nome:
            raise HTTPException(
                status_code=400,
                detail="Nome obrigatório para novo cadastro",
            )
        cliente = Cliente(nome=dados.nome, telefone=telefone)
        db.add(cliente)
        db.commit()

    cliente_id = cliente.id
    cliente_nome = cliente.nome
    cliente_telefone = cliente.telefone
    cliente_endereco = cliente.endereco_padrao
    cliente_total_pedidos = cliente.total_pedidos
    cliente_segmento = cliente.segmento
    cliente_criado_em = cliente.criado_em

    token = criar_token_cliente(cliente_id)

    return {
        "cliente": {
            "id": cliente_id,
            "nome": cliente_nome,
            "telefone": cliente_telefone,
            "endereco_padrao": cliente_endereco,
            "total_pedidos": cliente_total_pedidos,
            "segmento": cliente_segmento,
            "criado_em": cliente_criado_em,
        },
        "access_token": token,
        "token_type": "bearer",
    }


def atualizar_cliente(cliente_id: int, dados: ClienteUpdate, db: Session) -> Cliente:
    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)
    db.commit()
    return db.query(Cliente).filter(Cliente.id == cliente_id).first()