from __future__ import annotations
import pytest
from datetime import datetime
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
    PedidoCreate, PedidoAdminCreate, PedidoItemCreate, PedidoStatusUpdate,
    PedidoItemModificadorCreate,
)
from app.services.pedido_service import (
    criar_pedido, criar_pedido_admin, atualizar_status,
    deletar_pedido, deletar_pedidos_periodo, listar_pedidos,
)


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
    assert pedido.numero.startswith("ML-")
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

    assert "Menu Livre" in resultado["mensagem_whatsapp"]
    assert "ML-" in resultado["mensagem_whatsapp"]
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

# ── Helper com telefone único (evita UNIQUE constraint ao criar múltiplos pedidos) ──
_contador_telefone = 9000

def _criar_pedido_com_cliente_unico(db):
    """Cria pedido com um cliente de telefone único para evitar conflito de UNIQUE."""
    global _contador_telefone
    _contador_telefone += 1
    cat = Categoria(nome=f"Cat-{_contador_telefone}")
    db.add(cat)
    db.flush()
    produto = Produto(categoria_id=cat.id, nome="X", preco=10.0, disponivel=True)
    cliente = Cliente(nome="Teste", telefone=f"819999{_contador_telefone:05d}")
    db.add_all([produto, cliente])
    db.commit()
    return criar_pedido(
        PedidoCreate(
            tipo="retirada",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
        ),
        cliente.id,
        db,
    )["pedido"]


# ══════════════════════════════════════════════════════════
# DELETAR PEDIDO
# ══════════════════════════════════════════════════════════

def test_deletar_pedido_individual():
    db = setup_db()
    pedido = _criar_pedido_base(db)
    pedido_id = pedido.id

    deletar_pedido(pedido_id, db)

    from app.models.pedido import Pedido as PedidoModel
    assert db.get(PedidoModel, pedido_id) is None


def test_deletar_pedido_inexistente_retorna_404():
    db = setup_db()
    with pytest.raises(HTTPException) as exc:
        deletar_pedido(99999, db)
    assert exc.value.status_code == 404


def test_deletar_pedidos_periodo_hoje():
    """Deletar pedidos do periodo hoje remove todos do dia atual."""
    db = setup_db()

    _criar_pedido_com_cliente_unico(db)
    _criar_pedido_com_cliente_unico(db)

    total = deletar_pedidos_periodo("hoje", db)
    assert total == 2

    from app.models.pedido import Pedido as PedidoModel
    restantes = db.query(PedidoModel).count()
    assert restantes == 0


def test_deletar_pedidos_periodo_invalido():
    db = setup_db()
    with pytest.raises(HTTPException) as exc:
        deletar_pedidos_periodo("mes", db)
    assert exc.value.status_code == 400


# ══════════════════════════════════════════════════════════
# FILTRO POR DATA em listar_pedidos
# ══════════════════════════════════════════════════════════

def test_listar_pedidos_filtra_por_data_hoje():
    from datetime import date, timezone
    db = setup_db()

    _criar_pedido_com_cliente_unico(db)
    _criar_pedido_com_cliente_unico(db)

    # Filtra pelo dia UTC atual (mesma base usada pelo service)
    hoje_utc = datetime.now(timezone.utc).date()
    resultado = listar_pedidos(db, data_inicio=hoje_utc, data_fim=hoje_utc)
    assert len(resultado) == 2


def test_listar_pedidos_data_passada_retorna_vazio():
    """Filtrar por data passada (2020-01-01) não deve retornar pedidos criados agora."""
    from datetime import date
    db = setup_db()

    _criar_pedido_base(db)

    passado = date(2020, 1, 1)
    resultado = listar_pedidos(db, data_inicio=passado, data_fim=passado)
    assert len(resultado) == 0


# ══════════════════════════════════════════════════════════
# CRIAR PEDIDO ADMIN
# ══════════════════════════════════════════════════════════

def test_criar_pedido_admin_com_cliente_existente():
    db = setup_db()
    produto, cliente = criar_base(db)

    resultado = criar_pedido_admin(
        PedidoAdminCreate(
            tipo="balcao",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
            cliente_id=cliente.id,
        ),
        db,
    )

    pedido = resultado["pedido"]
    assert pedido.numero.startswith("ML-")
    assert pedido.tipo == "balcao"
    assert pedido.status == "pendente"
    assert pedido.total == 44.90


def test_criar_pedido_admin_cria_cliente_novo():
    db = setup_db()
    produto, _ = criar_base(db)

    resultado = criar_pedido_admin(
        PedidoAdminCreate(
            tipo="retirada",
            metodo_pagamento="dinheiro",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
            cliente_telefone="81999990099",
            cliente_nome="Joao da Silva",
        ),
        db,
    )

    pedido = resultado["pedido"]
    assert pedido.cliente.nome == "Joao da Silva"
    assert pedido.cliente.telefone == "81999990099"


def test_criar_pedido_admin_bypass_loja_fechada():
    """Admin consegue criar pedido mesmo com loja fechada manualmente."""
    db = setup_db()
    produto, cliente = criar_base(db)

    config = Configuracao(id=1, whatsapp="", fechado_manualmente=True, mensagem_fechado="Fechado")
    db.add(config)
    db.commit()

    resultado = criar_pedido_admin(
        PedidoAdminCreate(
            tipo="balcao",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
            cliente_id=cliente.id,
        ),
        db,
    )
    assert resultado["pedido"] is not None


def test_criar_pedido_admin_sem_cliente_usa_balcao():
    """Sem cliente_id nem telefone, o service cria/reutiliza o cliente sistema 'Balcão'."""
    db = setup_db()
    produto, _ = criar_base(db)

    config = Configuracao(id=1, whatsapp="")
    db.add(config)
    db.commit()

    resultado = criar_pedido_admin(
        PedidoAdminCreate(
            tipo="balcao",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
        ),
        db,
    )
    assert resultado["pedido"] is not None
    assert resultado["pedido"].cliente.nome == "Balcão"
