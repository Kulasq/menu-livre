from __future__ import annotations
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.database import Base
from app.models.categoria import Categoria
from app.models.produto import Produto
from app.models.cliente import Cliente
from app.models.configuracao import Configuracao
from app.schemas.pedido import PedidoCreate, PedidoItemCreate, PedidoStatusUpdate
from app.services.pedido_service import criar_pedido, atualizar_status


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def configurar(conn, rec):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def criar_base(db):
    """Cria categoria, produto e cliente para os testes."""
    cat = Categoria(nome="Hambúrgueres")
    db.add(cat)
    db.flush()

    produto = Produto(categoria_id=cat.id, nome="Bacontentão", preco=44.90, disponivel=True)
    db.add(produto)

    cliente = Cliente(nome="Lucas", telefone="81999990001")
    db.add(cliente)

    db.commit()
    return produto, cliente


def test_criar_pedido_retirada():
    db = setup_db()
    produto, cliente = criar_base(db)

    resultado = criar_pedido(
        PedidoCreate(
            tipo="retirada",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
        ),
        cliente.id,
        db,
    )

    pedido = resultado["pedido"]
    assert pedido.numero.startswith("PDM-")
    assert pedido.status == "pendente"
    assert pedido.total == 44.90
    assert pedido.taxa_entrega == 0.0
    assert len(pedido.itens) == 1


def test_criar_pedido_delivery_sem_endereco_falha():
    db = setup_db()
    produto, cliente = criar_base(db)

    with pytest.raises(HTTPException) as exc:
        criar_pedido(
            PedidoCreate(
                tipo="delivery",
                metodo_pagamento="pix",
                itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
            ),
            cliente.id,
            db,
        )
    assert exc.value.status_code == 400


def test_criar_pedido_produto_indisponivel_falha():
    db = setup_db()
    produto, cliente = criar_base(db)
    produto.disponivel = False
    db.commit()

    with pytest.raises(HTTPException) as exc:
        criar_pedido(
            PedidoCreate(
                tipo="retirada",
                metodo_pagamento="pix",
                itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
            ),
            cliente.id,
            db,
        )
    assert exc.value.status_code == 400


def test_fluxo_status_valido():
    db = setup_db()
    produto, cliente = criar_base(db)

    resultado = criar_pedido(
        PedidoCreate(
            tipo="retirada",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
        ),
        cliente.id,
        db,
    )
    pedido = resultado["pedido"]

    pedido = atualizar_status(pedido.id, PedidoStatusUpdate(status="confirmado"), db)
    assert pedido.status == "confirmado"

    pedido = atualizar_status(pedido.id, PedidoStatusUpdate(status="em_preparo"), db)
    assert pedido.status == "em_preparo"


def test_transicao_status_invalida():
    db = setup_db()
    produto, cliente = criar_base(db)

    resultado = criar_pedido(
        PedidoCreate(
            tipo="retirada",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
        ),
        cliente.id,
        db,
    )
    pedido = resultado["pedido"]

    with pytest.raises(HTTPException) as exc:
        atualizar_status(pedido.id, PedidoStatusUpdate(status="entregue"), db)
    assert exc.value.status_code == 400


def test_mensagem_whatsapp_gerada():
    db = setup_db()
    produto, cliente = criar_base(db)

    resultado = criar_pedido(
        PedidoCreate(
            tipo="retirada",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
        ),
        cliente.id,
        db,
    )

    assert "Pão de Mão" in resultado["mensagem_whatsapp"]
    assert "PDM-" in resultado["mensagem_whatsapp"]
    assert "Bacontentão" in resultado["mensagem_whatsapp"]
    assert resultado["whatsapp_url"].startswith("https://api.whatsapp.com/send/")