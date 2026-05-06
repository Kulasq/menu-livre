"""Testes unitários do estoque_service.

Cobre:
- ajustar_estoque_produto: todas as operações + validações
- ajustar_estoque_modificador: idem
- abater_estoque_pedido: produto sem controle, produto com controle,
  modificador com controle, estoque insuficiente (produto e opção)
- restaurar_estoque_pedido: cancelamento restaura produto e modificador
- helpers de disponibilidade efetiva
"""
from __future__ import annotations
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.database import Base
from app.models.categoria import Categoria
from app.models.produto import Produto
from app.models.modificador import GrupoModificador, Modificador
from app.models.cliente import Cliente
from app.models.pedido import Pedido, PedidoItem, PedidoItemModificador
from app.schemas.cardapio import EstoqueAjusteRequest
from app.schemas.pedido import (
    PedidoCreate, PedidoItemCreate, PedidoItemModificadorCreate, PedidoStatusUpdate,
)
from app.services.estoque_service import (
    ajustar_estoque_produto,
    ajustar_estoque_modificador,
    abater_estoque_pedido,
    restaurar_estoque_pedido,
    produto_disponivel_efetivo,
    modificador_disponivel_efetivo,
    _calcular_novo_estoque,
)
from app.services.pedido_service import criar_pedido, atualizar_status, deletar_pedido


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def configurar(conn, rec):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _produto(db, **kwargs) -> Produto:
    cat = Categoria(nome="Cat")
    db.add(cat)
    db.flush()
    defaults = dict(categoria_id=cat.id, nome="P", preco=10.0, disponivel=True)
    defaults.update(kwargs)
    p = Produto(**defaults)
    db.add(p)
    db.flush()
    return p


def _modificador(db, grupo=None, **kwargs) -> Modificador:
    if grupo is None:
        grupo = GrupoModificador(nome="G", obrigatorio=False, selecao_maxima=1)
        db.add(grupo)
        db.flush()
    defaults = dict(grupo_id=grupo.id, nome="Opção", preco_adicional=0.0, disponivel=True)
    defaults.update(kwargs)
    m = Modificador(**defaults)
    db.add(m)
    db.flush()
    return m


# ── helpers de disponibilidade ────────────────────────────────────────────────

def test_produto_disponivel_efetivo_sem_controle():
    db = setup_db()
    p = _produto(db, controle_estoque=False, estoque_atual=0)
    assert produto_disponivel_efetivo(p) is True


def test_produto_disponivel_efetivo_com_estoque():
    db = setup_db()
    p = _produto(db, controle_estoque=True, estoque_atual=5)
    assert produto_disponivel_efetivo(p) is True


def test_produto_disponivel_efetivo_esgotado():
    db = setup_db()
    p = _produto(db, controle_estoque=True, estoque_atual=0)
    assert produto_disponivel_efetivo(p) is False


def test_produto_indisponivel_flag_admin():
    db = setup_db()
    p = _produto(db, disponivel=False, controle_estoque=False)
    assert produto_disponivel_efetivo(p) is False


def test_modificador_disponivel_efetivo_sem_controle():
    db = setup_db()
    m = _modificador(db, controle_estoque=False, estoque_atual=0)
    assert modificador_disponivel_efetivo(m) is True


def test_modificador_disponivel_efetivo_com_estoque():
    db = setup_db()
    m = _modificador(db, controle_estoque=True, estoque_atual=3)
    assert modificador_disponivel_efetivo(m) is True


def test_modificador_disponivel_efetivo_esgotado():
    db = setup_db()
    m = _modificador(db, controle_estoque=True, estoque_atual=0)
    assert modificador_disponivel_efetivo(m) is False


# ── _calcular_novo_estoque ────────────────────────────────────────────────────

def test_calcular_definir():
    assert _calcular_novo_estoque(5, "definir", 10, "X") == 10


def test_calcular_incrementar():
    assert _calcular_novo_estoque(5, "incrementar", 3, "X") == 8


def test_calcular_decrementar():
    assert _calcular_novo_estoque(5, "decrementar", 2, "X") == 3


def test_calcular_zerar():
    assert _calcular_novo_estoque(5, "zerar", 0, "X") == 0


def test_calcular_decrementar_abaixo_de_zero_levanta():
    with pytest.raises(HTTPException) as exc:
        _calcular_novo_estoque(2, "decrementar", 5, "X")
    assert exc.value.status_code == 400


def test_calcular_definir_negativo_levanta():
    with pytest.raises(HTTPException):
        _calcular_novo_estoque(0, "definir", -1, "X")
    # Field(ge=0) no schema bloqueia isso antes; mas o helper tb valida
    # Valor 0 é válido:
    assert _calcular_novo_estoque(10, "definir", 0, "X") == 0


# ── ajustar_estoque_produto ───────────────────────────────────────────────────

def test_ajustar_produto_definir():
    db = setup_db()
    p = _produto(db, controle_estoque=True, estoque_atual=3)
    db.commit()
    resultado = ajustar_estoque_produto(p.id, EstoqueAjusteRequest(operacao="definir", valor=10), db)
    assert resultado.estoque_atual == 10


def test_ajustar_produto_incrementar():
    db = setup_db()
    p = _produto(db, controle_estoque=True, estoque_atual=5)
    db.commit()
    resultado = ajustar_estoque_produto(p.id, EstoqueAjusteRequest(operacao="incrementar", valor=2), db)
    assert resultado.estoque_atual == 7


def test_ajustar_produto_decrementar():
    db = setup_db()
    p = _produto(db, controle_estoque=True, estoque_atual=5)
    db.commit()
    resultado = ajustar_estoque_produto(p.id, EstoqueAjusteRequest(operacao="decrementar", valor=3), db)
    assert resultado.estoque_atual == 2


def test_ajustar_produto_zerar():
    db = setup_db()
    p = _produto(db, controle_estoque=True, estoque_atual=5)
    db.commit()
    resultado = ajustar_estoque_produto(p.id, EstoqueAjusteRequest(operacao="zerar", valor=0), db)
    assert resultado.estoque_atual == 0


def test_ajustar_produto_nao_encontrado():
    db = setup_db()
    with pytest.raises(HTTPException) as exc:
        ajustar_estoque_produto(9999, EstoqueAjusteRequest(operacao="zerar", valor=0), db)
    assert exc.value.status_code == 404


def test_ajustar_produto_decrementar_abaixo_zero():
    db = setup_db()
    p = _produto(db, controle_estoque=True, estoque_atual=2)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        ajustar_estoque_produto(p.id, EstoqueAjusteRequest(operacao="decrementar", valor=5), db)
    assert exc.value.status_code == 400


# ── ajustar_estoque_modificador ───────────────────────────────────────────────

def test_ajustar_modificador_definir():
    db = setup_db()
    m = _modificador(db, controle_estoque=True, estoque_atual=0)
    db.commit()
    resultado = ajustar_estoque_modificador(m.id, EstoqueAjusteRequest(operacao="definir", valor=5), db)
    assert resultado.estoque_atual == 5


def test_ajustar_modificador_nao_encontrado():
    db = setup_db()
    with pytest.raises(HTTPException) as exc:
        ajustar_estoque_modificador(9999, EstoqueAjusteRequest(operacao="zerar", valor=0), db)
    assert exc.value.status_code == 404


# ── abater + restaurar via pedido_service (integração de service) ─────────────

def _setup_loja(db):
    """Cria cliente e config mínima para criar_pedido."""
    from app.models.configuracao import Configuracao
    cliente = Cliente(nome="Teste", telefone="81999990099")
    config = Configuracao(
        id=1, nome_loja="Teste", whatsapp="5581900000000",
        fechado_manualmente=False, aceitar_agendamentos=False,
    )
    db.add_all([cliente, config])
    db.commit()
    return cliente


def test_cancelar_pedido_restaura_estoque_produto():
    """Pedido cancelado devolve estoque ao produto."""
    db = setup_db()
    cliente = _setup_loja(db)
    cat = Categoria(nome="C")
    db.add(cat)
    db.flush()
    produto = Produto(
        categoria_id=cat.id, nome="Produto A", preco=20.0, disponivel=True,
        controle_estoque=True, estoque_atual=5,
    )
    db.add(produto)
    db.commit()

    resultado = criar_pedido(
        PedidoCreate(
            tipo="retirada",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=2)],
        ),
        cliente.id,
        db,
    )
    pedido = resultado["pedido"]
    db.refresh(produto)
    assert produto.estoque_atual == 3

    atualizar_status(pedido.id, PedidoStatusUpdate(status="cancelado"), db)
    db.refresh(produto)
    assert produto.estoque_atual == 5  # restaurado


def test_cancelar_pedido_restaura_estoque_modificador():
    """Pedido cancelado devolve estoque ao modificador selecionado."""
    db = setup_db()
    cliente = _setup_loja(db)
    cat = Categoria(nome="C")
    db.add(cat)
    db.flush()
    produto = Produto(
        categoria_id=cat.id, nome="Doce", preco=15.0, disponivel=True,
    )
    grupo = GrupoModificador(nome="Sabor", obrigatorio=False, selecao_maxima=1)
    db.add_all([produto, grupo])
    db.flush()
    opcao = Modificador(
        grupo_id=grupo.id, nome="Morango", preco_adicional=0.0, disponivel=True,
        controle_estoque=True, estoque_atual=4,
    )
    db.add(opcao)
    # Vincular grupo ao produto
    from app.models.modificador import produto_grupo_modificador
    db.execute(produto_grupo_modificador.insert().values(
        produto_id=produto.id, grupo_id=grupo.id, ordem=1
    ))
    db.commit()

    resultado = criar_pedido(
        PedidoCreate(
            tipo="retirada",
            metodo_pagamento="pix",
            itens=[PedidoItemCreate(
                produto_id=produto.id,
                quantidade=2,
                modificadores=[PedidoItemModificadorCreate(modificador_id=opcao.id)],
            )],
        ),
        cliente.id,
        db,
    )
    pedido = resultado["pedido"]
    db.refresh(opcao)
    assert opcao.estoque_atual == 2  # abateu 2

    atualizar_status(pedido.id, PedidoStatusUpdate(status="cancelado"), db)
    db.refresh(opcao)
    assert opcao.estoque_atual == 4  # restaurado


def test_deletar_pedido_nao_entregue_restaura_estoque():
    """Excluir pedido não-entregue devolve estoque."""
    db = setup_db()
    cliente = _setup_loja(db)
    cat = Categoria(nome="C")
    db.add(cat)
    db.flush()
    produto = Produto(
        categoria_id=cat.id, nome="Item", preco=10.0, disponivel=True,
        controle_estoque=True, estoque_atual=3,
    )
    db.add(produto)
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
    db.refresh(produto)
    assert produto.estoque_atual == 2

    deletar_pedido(pedido.id, db)
    db.refresh(produto)
    assert produto.estoque_atual == 3  # restaurado


def test_deletar_pedido_entregue_nao_restaura_estoque():
    """Excluir pedido entregue NÃO devolve estoque — produto já foi consumido."""
    db = setup_db()
    cliente = _setup_loja(db)
    cat = Categoria(nome="C")
    db.add(cat)
    db.flush()
    produto = Produto(
        categoria_id=cat.id, nome="Item", preco=10.0, disponivel=True,
        controle_estoque=True, estoque_atual=3,
    )
    db.add(produto)
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
    # Percorrer status até entregue
    atualizar_status(pedido.id, PedidoStatusUpdate(status="confirmado"), db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="em_preparo"), db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="pronto"), db)
    atualizar_status(pedido.id, PedidoStatusUpdate(status="entregue"), db)

    db.refresh(produto)
    estoque_pos_entrega = produto.estoque_atual  # == 2

    deletar_pedido(pedido.id, db)
    db.refresh(produto)
    assert produto.estoque_atual == estoque_pos_entrega  # não restaurou


def test_estoque_insuficiente_modificador_bloqueia_pedido():
    """Pedido com opção de modificador esgotada retorna 400."""
    db = setup_db()
    cliente = _setup_loja(db)
    cat = Categoria(nome="C")
    db.add(cat)
    db.flush()
    produto = Produto(
        categoria_id=cat.id, nome="Doce", preco=10.0, disponivel=True,
    )
    grupo = GrupoModificador(nome="Sabor", obrigatorio=False, selecao_maxima=1)
    db.add_all([produto, grupo])
    db.flush()
    opcao = Modificador(
        grupo_id=grupo.id, nome="Baunilha", preco_adicional=0.0, disponivel=True,
        controle_estoque=True, estoque_atual=0,  # ESGOTADO
    )
    db.add(opcao)
    from app.models.modificador import produto_grupo_modificador
    db.execute(produto_grupo_modificador.insert().values(
        produto_id=produto.id, grupo_id=grupo.id, ordem=1
    ))
    db.commit()

    with pytest.raises(HTTPException) as exc:
        criar_pedido(
            PedidoCreate(
                tipo="retirada",
                metodo_pagamento="pix",
                itens=[PedidoItemCreate(
                    produto_id=produto.id,
                    quantidade=1,
                    modificadores=[PedidoItemModificadorCreate(modificador_id=opcao.id)],
                )],
            ),
            cliente.id,
            db,
        )
    assert exc.value.status_code == 400
    assert "estoque" in exc.value.detail.lower()


def test_dois_abates_consecutivos_esgotam():
    """Dois pedidos consecutivos do mesmo produto esgotam o estoque corretamente."""
    db = setup_db()
    cliente = _setup_loja(db)
    cat = Categoria(nome="C")
    db.add(cat)
    db.flush()
    produto = Produto(
        categoria_id=cat.id, nome="Último item", preco=10.0, disponivel=True,
        controle_estoque=True, estoque_atual=1,
    )
    db.add(produto)
    db.commit()

    # Primeiro pedido — passa
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

    # Segundo pedido — bloqueia
    cliente2 = Cliente(nome="Outro", telefone="81999990001")
    db.add(cliente2)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        criar_pedido(
            PedidoCreate(
                tipo="retirada",
                metodo_pagamento="pix",
                itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
            ),
            cliente2.id,
            db,
        )
    assert exc.value.status_code == 400
