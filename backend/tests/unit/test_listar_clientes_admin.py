from __future__ import annotations
import pytest
from datetime import datetime, timezone, timedelta

from app.models.cliente import Cliente
from app.services.cliente_service import listar_clientes_admin


def _add_cliente(db, nome, telefone, total_pedidos=0, total_gasto=0.0, segmento="novo", dias=None):
    c = Cliente(nome=nome, telefone=telefone)
    c.total_pedidos = total_pedidos
    c.total_gasto = total_gasto
    c.segmento = segmento
    c.ultimo_pedido = datetime.now(timezone.utc) - timedelta(days=dias) if dias is not None else None
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def clientes(db_teste):
    _add_cliente(db_teste, "Ana Lima", "81911110000", total_pedidos=10, total_gasto=350.0, segmento="campeao", dias=5)
    _add_cliente(db_teste, "Bruno Costa", "81922220000", total_pedidos=3, total_gasto=90.0, segmento="leal", dias=20)
    _add_cliente(db_teste, "Carla Souza", "81933330000", total_pedidos=1, total_gasto=30.0, segmento="novo", dias=2)
    _add_cliente(db_teste, "Diego Alves", "81944440000", total_pedidos=5, total_gasto=180.0, segmento="em_risco", dias=60)
    db_teste.commit()


def test_listar_todos(db_teste, clientes):
    resultado, total = listar_clientes_admin(db_teste)
    assert total == 4
    assert len(resultado) == 4


def test_busca_por_nome(db_teste, clientes):
    resultado, total = listar_clientes_admin(db_teste, q="ana")
    assert total == 1
    assert resultado[0].nome == "Ana Lima"


def test_busca_por_telefone(db_teste, clientes):
    resultado, total = listar_clientes_admin(db_teste, q="81933")
    assert total == 1
    assert resultado[0].nome == "Carla Souza"


def test_busca_sem_resultado(db_teste, clientes):
    resultado, total = listar_clientes_admin(db_teste, q="naoexiste")
    assert total == 0
    assert resultado == []


def test_filtro_segmento(db_teste, clientes):
    resultado, total = listar_clientes_admin(db_teste, segmento="leal")
    assert total == 1
    assert resultado[0].nome == "Bruno Costa"


def test_filtro_segmento_inexistente(db_teste, clientes):
    resultado, total = listar_clientes_admin(db_teste, segmento="inativo")
    assert total == 0


def test_ordenar_por_nome(db_teste, clientes):
    resultado, _ = listar_clientes_admin(db_teste, ordenar="nome")
    nomes = [c.nome for c in resultado]
    assert nomes == sorted(nomes)


def test_ordenar_por_total_gasto(db_teste, clientes):
    resultado, _ = listar_clientes_admin(db_teste, ordenar="total_gasto")
    gastos = [c.total_gasto for c in resultado]
    assert gastos == sorted(gastos, reverse=True)


def test_ordenar_por_total_pedidos(db_teste, clientes):
    resultado, _ = listar_clientes_admin(db_teste, ordenar="total_pedidos")
    pedidos = [c.total_pedidos for c in resultado]
    assert pedidos == sorted(pedidos, reverse=True)


def test_ordenar_invalido_usa_padrao(db_teste, clientes):
    # Não deve lançar exceção — cai para ordenação padrão (ultimo_pedido)
    resultado, total = listar_clientes_admin(db_teste, ordenar="campo_inexistente")
    assert total == 4


def test_paginacao(db_teste, clientes):
    pagina1, total = listar_clientes_admin(db_teste, page=1, page_size=2)
    pagina2, _ = listar_clientes_admin(db_teste, page=2, page_size=2)
    assert total == 4
    assert len(pagina1) == 2
    assert len(pagina2) == 2
    ids_p1 = {c.id for c in pagina1}
    ids_p2 = {c.id for c in pagina2}
    assert ids_p1.isdisjoint(ids_p2)


def test_paginacao_pagina_alem_do_total(db_teste, clientes):
    resultado, total = listar_clientes_admin(db_teste, page=99, page_size=30)
    assert total == 4
    assert resultado == []


def test_filtro_combinado(db_teste, clientes):
    resultado, total = listar_clientes_admin(db_teste, q="Bruno", segmento="leal")
    assert total == 1
    assert resultado[0].nome == "Bruno Costa"
