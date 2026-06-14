"""Testes da branch fix/pedido-transacao-atomica.

Cobre:
- Pedido + uso de cupom + stats do cliente commitados na MESMA transação.
- Falha no meio da transação desfaz o pedido inteiro (rollback) — sem pedido
  órfão, sem cupom incrementado, sem estoque abatido, sem stats alteradas.
- Cupom com limite_total_usos=1 aplicado 2x não ultrapassa 1 uso.
- Estoque nunca fica negativo em pedidos sequenciais que disputam a última unidade.

Nota: SQLite in-memory single-connection não permite simular concorrência real,
então o lock (with_for_update) é um no-op aqui — o que validamos é o comportamento
do guard sequencial e a atomicidade do commit único.
"""
from __future__ import annotations
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.database import Base
from app.models.categoria import Categoria
from app.models.produto import Produto
from app.models.cliente import Cliente
from app.models.cupom import Cupom, CupomUso
from app.models.pedido import Pedido
from app.schemas.pedido import PedidoCreate, PedidoItemCreate
from app.services import cupom_service
from app.services.pedido_service import criar_pedido


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _fk(conn, rec):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


_tel = 8200000000


def _base(db, *, preco=50.0, estoque=None):
    """Cria categoria + produto + cliente (telefone único). estoque liga controle."""
    global _tel
    _tel += 1
    cat = Categoria(nome=f"Cat-{_tel}")
    db.add(cat)
    db.flush()
    kwargs = dict(categoria_id=cat.id, nome="X", preco=preco, disponivel=True)
    if estoque is not None:
        kwargs.update(controle_estoque=True, estoque_atual=estoque)
    produto = Produto(**kwargs)
    cliente = Cliente(nome="Teste", telefone=str(_tel))
    db.add_all([produto, cliente])
    db.commit()
    return produto, cliente


def _pedido_com_cupom(db, produto, cliente, codigo):
    return criar_pedido(
        PedidoCreate(
            tipo="retirada",
            metodo_pagamento="pix",
            cupom_codigo=codigo,
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
        ),
        cliente.id,
        db,
    )


def _boom(*args, **kwargs):
    raise RuntimeError("falha simulada dentro da transação")


# ── Atomicidade do commit único ──────────────────────────────────────────────

def test_pedido_cupom_e_stats_commitados_juntos():
    db = setup_db()
    produto, cliente = _base(db, preco=100.0)
    db.add(Cupom(codigo="DEZ", tipo="valor_fixo", valor=10.0, ativo=True))
    db.commit()

    resultado = _pedido_com_cupom(db, produto, cliente, "DEZ")
    pedido = resultado["pedido"]

    assert pedido.desconto_cupom == pytest.approx(10.0)
    assert pedido.total == pytest.approx(90.0)

    cupom = db.query(Cupom).filter_by(codigo="DEZ").first()
    assert cupom.usos_atuais == 1

    usos = db.query(CupomUso).filter_by(cupom_id=cupom.id).all()
    assert len(usos) == 1
    assert usos[0].pedido_id == pedido.id

    db.refresh(cliente)
    assert cliente.total_pedidos == 1
    assert cliente.total_gasto == pytest.approx(90.0)


def test_falha_no_registro_de_uso_desfaz_pedido_inteiro(monkeypatch):
    """Se registrar_uso_cupom falha, o commit único nunca acontece: rollback
    completo — sem pedido, sem CupomUso, cupom volta a 0 usos, stats intactas."""
    db = setup_db()
    produto, cliente = _base(db, preco=100.0)
    db.add(Cupom(codigo="DEZ", tipo="valor_fixo", valor=10.0, ativo=True))
    db.commit()

    monkeypatch.setattr(cupom_service, "registrar_uso_cupom", _boom)

    with pytest.raises(RuntimeError):
        _pedido_com_cupom(db, produto, cliente, "DEZ")

    assert db.query(Pedido).count() == 0
    assert db.query(CupomUso).count() == 0

    cupom = db.query(Cupom).filter_by(codigo="DEZ").first()
    assert cupom.usos_atuais == 0  # incremento revertido pelo rollback

    db.refresh(cliente)
    assert cliente.total_pedidos == 0
    assert cliente.total_gasto == pytest.approx(0.0)


def test_rollback_restaura_estoque_abatido(monkeypatch):
    """Estoque abatido durante a transação volta ao original se o commit falha."""
    db = setup_db()
    produto, cliente = _base(db, preco=100.0, estoque=5)
    db.add(Cupom(codigo="DEZ", tipo="valor_fixo", valor=10.0, ativo=True))
    db.commit()

    monkeypatch.setattr(cupom_service, "registrar_uso_cupom", _boom)

    with pytest.raises(RuntimeError):
        _pedido_com_cupom(db, produto, cliente, "DEZ")

    db.refresh(produto)
    assert produto.estoque_atual == 5  # abate revertido — nada commitado


# ── Race condition de cupom ───────────────────────────────────────────────────

def test_cupom_limite_total_um_aplicado_duas_vezes_nao_passa_de_um():
    db = setup_db()
    produto, cliente = _base(db, preco=100.0)
    db.add(Cupom(codigo="UNICO", tipo="valor_fixo", valor=10.0,
                 ativo=True, limite_total_usos=1))
    db.commit()

    # 1º uso: ok
    _pedido_com_cupom(db, produto, cliente, "UNICO")

    # 2º uso: cupom esgotado
    with pytest.raises(HTTPException) as exc:
        _pedido_com_cupom(db, produto, cliente, "UNICO")
    assert exc.value.status_code == 400
    assert "esgotado" in exc.value.detail.lower()

    cupom = db.query(Cupom).filter_by(codigo="UNICO").first()
    assert cupom.usos_atuais == 1
    assert db.query(CupomUso).filter_by(cupom_id=cupom.id).count() == 1


def test_reaplicar_cupom_esgotado_dentro_do_lock_levanta_400():
    """Exercita o re-check sob lock em aplicar_cupom_no_pedido: mesmo que a
    validação inicial passe, incrementar além do limite é bloqueado."""
    db = setup_db()
    _base(db)  # só pra ter telefone/cliente coerentes no banco
    db.add(Cupom(codigo="LIM", tipo="valor_fixo", valor=5.0,
                 ativo=True, limite_total_usos=1, usos_atuais=0))
    db.commit()

    # Primeiro incremento leva usos_atuais a 1 (dentro do limite)
    cupom_service.aplicar_cupom_no_pedido("LIM", 50.0, None, db)
    # Segundo incremento: o re-check sob lock vê usos_atuais >= limite e barra
    with pytest.raises(HTTPException) as exc:
        cupom_service.aplicar_cupom_no_pedido("LIM", 50.0, None, db)
    assert exc.value.status_code == 400

    cupom = db.query(Cupom).filter_by(codigo="LIM").first()
    assert cupom.usos_atuais == 1


# ── Race condition de estoque ─────────────────────────────────────────────────

def test_estoque_nunca_fica_negativo_em_pedidos_sequenciais():
    db = setup_db()
    produto, cliente1 = _base(db, preco=10.0, estoque=1)
    _, cliente2 = _base(db, preco=10.0)  # outro cliente (produto extra ignorado)

    # 1º pedido consome a última unidade
    criar_pedido(
        PedidoCreate(
            tipo="retirada", metodo_pagamento="pix",
            itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
        ),
        cliente1.id, db,
    )
    db.refresh(produto)
    assert produto.estoque_atual == 0

    # 2º pedido do mesmo produto falha — sem estoque
    with pytest.raises(HTTPException) as exc:
        criar_pedido(
            PedidoCreate(
                tipo="retirada", metodo_pagamento="pix",
                itens=[PedidoItemCreate(produto_id=produto.id, quantidade=1)],
            ),
            cliente2.id, db,
        )
    assert exc.value.status_code == 400
    assert "estoque" in exc.value.detail.lower()

    db.refresh(produto)
    assert produto.estoque_atual == 0  # nunca negativo
