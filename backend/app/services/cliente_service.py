from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.cliente import Cliente, Endereco
from app.schemas.cliente import ClienteIdentificar, ClienteUpdate
from app.services.auth_service import criar_token_cliente
import re

_LIMITE_ENDERECOS = 5


def _dias_desde_ultimo_pedido(cliente: Cliente) -> int | None:
    if not cliente.ultimo_pedido:
        return None
    ultimo = cliente.ultimo_pedido
    if ultimo.tzinfo is None:
        ultimo = ultimo.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ultimo).days


def calcular_segmento_rfm(cliente: Cliente) -> str:
    """Classifica o cliente por Recência, Frequência e Monetário."""
    if cliente.total_pedidos == 0:
        return "novo"

    dias = _dias_desde_ultimo_pedido(cliente)

    # Inativo: mais de 90 dias sem pedir
    if dias is not None and dias > 90:
        return "inativo"

    # Novo: apenas 1 pedido
    if cliente.total_pedidos == 1:
        return "novo"

    # Campeão: recente + frequente + bom gasto
    if (dias is not None and dias <= 15
            and cliente.total_pedidos >= 5
            and cliente.total_gasto > 200):
        return "campeao"

    # Leal: recente + frequência média/alta
    if dias is not None and dias <= 30 and cliente.total_pedidos >= 3:
        return "leal"

    # Em risco: frequente mas sumiu há mais de 45 dias
    if cliente.total_pedidos >= 3 and dias is not None and dias > 45:
        return "em_risco"

    return "comum"


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
        # Cliente existente — atualiza nome se fornecido e recalcula segmento
        changed = False
        if dados.nome and dados.nome != cliente.nome:
            cliente.nome = dados.nome
            changed = True
        novo_segmento = calcular_segmento_rfm(cliente)
        if cliente.segmento != novo_segmento:
            cliente.segmento = novo_segmento
            changed = True
        if changed:
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


def listar_enderecos(db: Session, cliente_id: int) -> list[Endereco]:
    return (
        db.query(Endereco)
        .filter(Endereco.cliente_id == cliente_id)
        .order_by(Endereco.criado_em.desc())
        .all()
    )


def deletar_endereco(db: Session, endereco_id: int, cliente_id: int) -> None:
    endereco = db.get(Endereco, endereco_id)
    if not endereco:
        raise HTTPException(status_code=404, detail="Endereço não encontrado")
    if endereco.cliente_id != cliente_id:
        raise HTTPException(status_code=403, detail="Sem permissão para deletar este endereço")
    db.delete(endereco)
    db.commit()


def salvar_endereco_se_novo(db: Session, cliente_id: int, endereco: str) -> None:
    """Salva endereço se ainda não existir. Remove os mais antigos quando passa do limite."""
    texto = endereco.strip().lower()
    if not texto:
        return

    ja_existe = (
        db.query(Endereco)
        .filter(Endereco.cliente_id == cliente_id)
        .all()
    )

    for e in ja_existe:
        if e.endereco.strip().lower() == texto:
            return  # endereço idêntico já salvo

    novo = Endereco(cliente_id=cliente_id, endereco=endereco.strip())
    db.add(novo)

    # Remover os mais antigos se ultrapassar o limite
    total = len(ja_existe) + 1
    if total > _LIMITE_ENDERECOS:
        mais_antigos = sorted(ja_existe, key=lambda e: e.criado_em)
        para_remover = total - _LIMITE_ENDERECOS
        for antigo in mais_antigos[:para_remover]:
            db.delete(antigo)

    db.commit()