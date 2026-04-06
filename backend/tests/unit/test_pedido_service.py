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
from app.models.modificador import GrupoModificador, Modificador
from app.schemas.pedido import (
    PedidoCreate, PedidoItemCreate, PedidoStatusUpdate,
    PedidoItemModificadorCreate,
)
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


# ── Helper para criar pedido rapidamente ─────────────────────────────────────

def _criar_pedido_base(db):
    """Cria e retorna um pedido no status inicial (pendente)."""
    produto, cliente = criar_base(db)
    return criar_pedido(
        PedidoCreate(
            tipo="retirada",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
        ),
        cliente.id,
        db,
    )["pedido"]


# ── Matriz completa de transições de status ───────────────────────────────────

def test_status_pendente_para_cancelado():
    db = setup_db()
    pedido = _criar_pedido_base(db)
    pedido = atualizar_status(pedido.id, PedidoStatusUpdate(status="cancelado"), db)
    assert pedido.status == "cancelado"


def test_status_confirmado_para_cancelado():
    db = setup_db()
    pedido = _criar_pedido_base(db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="confirmado"), db)
    pedido = atualizar_status(pedido.id, PedidoStatusUpdate(status="cancelado"), db)
    assert pedido.status == "cancelado"


def test_status_em_preparo_para_pronto():
    db = setup_db()
    pedido = _criar_pedido_base(db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="confirmado"), db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="em_preparo"), db)
    pedido = atualizar_status(pedido.id, PedidoStatusUpdate(status="pronto"), db)
    assert pedido.status == "pronto"


def test_status_pronto_para_entregue():
    db = setup_db()
    pedido = _criar_pedido_base(db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="confirmado"), db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="em_preparo"), db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="pronto"), db)
    pedido = atualizar_status(pedido.id, PedidoStatusUpdate(status="entregue"), db)
    assert pedido.status == "entregue"


def test_status_entregue_nao_transiciona():
    """Pedido entregue é estado final — qualquer transição deve falhar."""
    db = setup_db()
    pedido = _criar_pedido_base(db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="confirmado"), db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="em_preparo"), db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="pronto"), db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="entregue"), db)

    with pytest.raises(HTTPException) as exc:
        atualizar_status(pedido.id, PedidoStatusUpdate(status="confirmado"), db)
    assert exc.value.status_code == 400


def test_status_cancelado_nao_transiciona():
    """Pedido cancelado é estado final — qualquer transição deve falhar."""
    db = setup_db()
    pedido = _criar_pedido_base(db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="cancelado"), db)

    with pytest.raises(HTTPException) as exc:
        atualizar_status(pedido.id, PedidoStatusUpdate(status="confirmado"), db)
    assert exc.value.status_code == 400


def test_em_preparo_nao_pode_cancelar():
    """Em preparo não pode voltar para cancelado — proteção operacional."""
    db = setup_db()
    pedido = _criar_pedido_base(db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="confirmado"), db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="em_preparo"), db)

    with pytest.raises(HTTPException) as exc:
        atualizar_status(pedido.id, PedidoStatusUpdate(status="cancelado"), db)
    assert exc.value.status_code == 400


# ── Cálculo de valores ────────────────────────────────────────────────────────

def test_delivery_aplica_taxa_entrega_da_config():
    db = setup_db()
    cat = Categoria(nome="H")
    db.add(cat)
    db.flush()
    produto = Produto(categoria_id=cat.id, nome="X", preco=30.0, disponivel=True)
    cliente = Cliente(nome="Lucas", telefone="81999990010")
    config = Configuracao(id=1, whatsapp="", taxa_entrega=5.0)
    db.add_all([produto, cliente, config])
    db.commit()

    resultado = criar_pedido(
        PedidoCreate(
            tipo="delivery",
            endereco_entrega="Rua A, 1",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
        ),
        cliente.id,
        db,
    )
    pedido = resultado["pedido"]
    assert pedido.taxa_entrega == 5.0
    assert pedido.total == pytest.approx(35.0)


def test_retirada_taxa_entrega_sempre_zero():
    db = setup_db()
    cat = Categoria(nome="H")
    db.add(cat)
    db.flush()
    produto = Produto(categoria_id=cat.id, nome="X", preco=30.0, disponivel=True)
    cliente = Cliente(nome="Lucas", telefone="81999990011")
    config = Configuracao(id=1, whatsapp="", taxa_entrega=5.0)
    db.add_all([produto, cliente, config])
    db.commit()

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
    assert pedido.taxa_entrega == 0.0
    assert pedido.total == pytest.approx(30.0)


def test_subtotal_calculado_somando_itens():
    """Subtotal = soma de (preco * quantidade) para cada item."""
    db = setup_db()
    produto, cliente = criar_base(db)  # preco=44.90

    resultado = criar_pedido(
        PedidoCreate(
            tipo="retirada",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=3)],
        ),
        cliente.id,
        db,
    )
    pedido = resultado["pedido"]
    assert pedido.subtotal == pytest.approx(44.90 * 3)
    assert pedido.total == pytest.approx(44.90 * 3)


# ── Pedido mínimo ─────────────────────────────────────────────────────────────

def test_pedido_minimo_rejeita_pedido_abaixo_do_minimo():
    db = setup_db()
    cat = Categoria(nome="H")
    db.add(cat)
    db.flush()
    produto = Produto(categoria_id=cat.id, nome="X", preco=20.0, disponivel=True)
    cliente = Cliente(nome="Lucas", telefone="81999990012")
    config = Configuracao(id=1, whatsapp="", pedido_minimo=50.0)
    db.add_all([produto, cliente, config])
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
    assert "mínimo" in exc.value.detail.lower()


# ── Controle de estoque ───────────────────────────────────────────────────────

def test_estoque_decrementado_ao_criar_pedido():
    db = setup_db()
    cat = Categoria(nome="H")
    db.add(cat)
    db.flush()
    produto = Produto(
        categoria_id=cat.id, nome="X", preco=10.0, disponivel=True,
        controle_estoque=True, estoque_atual=5,
    )
    cliente = Cliente(nome="Lucas", telefone="81999990013")
    db.add_all([produto, cliente])
    db.commit()

    criar_pedido(
        PedidoCreate(
            tipo="retirada",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=2)],
        ),
        cliente.id,
        db,
    )
    db.refresh(produto)
    assert produto.estoque_atual == 3


def test_estoque_zero_torna_produto_indisponivel():
    db = setup_db()
    cat = Categoria(nome="H")
    db.add(cat)
    db.flush()
    produto = Produto(
        categoria_id=cat.id, nome="X", preco=10.0, disponivel=True,
        controle_estoque=True, estoque_atual=1,
    )
    cliente = Cliente(nome="Lucas", telefone="81999990014")
    db.add_all([produto, cliente])
    db.commit()

    criar_pedido(
        PedidoCreate(
            tipo="retirada",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
        ),
        cliente.id,
        db,
    )
    db.refresh(produto)
    assert produto.estoque_atual == 0
    assert produto.disponivel is False


def test_estoque_insuficiente_rejeita_pedido():
    db = setup_db()
    cat = Categoria(nome="H")
    db.add(cat)
    db.flush()
    produto = Produto(
        categoria_id=cat.id, nome="X", preco=10.0, disponivel=True,
        controle_estoque=True, estoque_atual=1,
    )
    cliente = Cliente(nome="Lucas", telefone="81999990015")
    db.add_all([produto, cliente])
    db.commit()

    with pytest.raises(HTTPException) as exc:
        criar_pedido(
            PedidoCreate(
                tipo="retirada",
                metodo_pagamento="pix",
                itens=[PedidoItemCreate(produto_id=produto.id, quantidade=5)],
            ),
            cliente.id,
            db,
        )
    assert exc.value.status_code == 400
    assert "estoque" in exc.value.detail.lower()


# ── Stats do cliente ──────────────────────────────────────────────────────────

def test_stats_cliente_atualizados_apos_pedido():
    db = setup_db()
    produto, cliente = criar_base(db)  # preco=44.90
    assert cliente.total_pedidos == 0

    criar_pedido(
        PedidoCreate(
            tipo="retirada",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
        ),
        cliente.id,
        db,
    )
    db.refresh(cliente)
    assert cliente.total_pedidos == 1
    assert cliente.total_gasto == pytest.approx(44.90)
    assert cliente.ultimo_pedido is not None


# ── Modificadores ─────────────────────────────────────────────────────────────

def test_modificador_preco_adicional_incluido_no_subtotal():
    db = setup_db()
    cat = Categoria(nome="H")
    db.add(cat)
    db.flush()
    produto = Produto(categoria_id=cat.id, nome="X", preco=30.0, disponivel=True)
    db.add(produto)
    db.flush()

    grupo = GrupoModificador(produto_id=produto.id, nome="Adicionais", obrigatorio=False)
    db.add(grupo)
    db.flush()

    mod = Modificador(grupo_id=grupo.id, nome="Bacon extra", preco_adicional=5.0, disponivel=True)
    db.add(mod)

    cliente = Cliente(nome="Lucas", telefone="81999990016")
    db.add(cliente)
    db.commit()

    resultado = criar_pedido(
        PedidoCreate(
            tipo="retirada",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(
                produto_id=produto.id,
                quantidade=1,
                modificadores=[PedidoItemModificadorCreate(modificador_id=mod.id)],
            )],
        ),
        cliente.id,
        db,
    )
    pedido = resultado["pedido"]
    assert pedido.subtotal == pytest.approx(35.0)  # 30 + 5
    assert pedido.itens[0].preco_snapshot == pytest.approx(35.0)


def test_modificador_indisponivel_rejeita_pedido():
    db = setup_db()
    cat = Categoria(nome="H")
    db.add(cat)
    db.flush()
    produto = Produto(categoria_id=cat.id, nome="X", preco=30.0, disponivel=True)
    db.add(produto)
    db.flush()

    grupo = GrupoModificador(produto_id=produto.id, nome="Adicionais", obrigatorio=False)
    db.add(grupo)
    db.flush()

    mod = Modificador(grupo_id=grupo.id, nome="Bacon", preco_adicional=5.0, disponivel=False)
    db.add(mod)

    cliente = Cliente(nome="Lucas", telefone="81999990017")
    db.add(cliente)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        criar_pedido(
            PedidoCreate(
                tipo="retirada",
                metodo_pagamento="pix",
                itens=[PedidoItemCreate(
                    produto_id=produto.id,
                    quantidade=1,
                    modificadores=[PedidoItemModificadorCreate(modificador_id=mod.id)],
                )],
            ),
            cliente.id,
            db,
        )
    assert exc.value.status_code == 400