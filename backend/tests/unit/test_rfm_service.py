from __future__ import annotations
from datetime import datetime, timezone, timedelta

from app.models.cliente import Cliente
from app.services.cliente_service import calcular_segmento_rfm


def _cliente(total_pedidos=0, total_gasto=0.0, dias_desde_ultimo=None):
    c = Cliente(nome="Teste", telefone="81999990000")
    c.total_pedidos = total_pedidos
    c.total_gasto = total_gasto
    if dias_desde_ultimo is not None:
        c.ultimo_pedido = datetime.now(timezone.utc) - timedelta(days=dias_desde_ultimo)
    else:
        c.ultimo_pedido = None
    c.segmento = "novo"
    return c


# ── casos base ────────────────────────────────────────────────────────────────

def test_segmento_novo_sem_pedidos():
    c = _cliente(total_pedidos=0)
    assert calcular_segmento_rfm(c) == "novo"


def test_segmento_novo_um_pedido():
    c = _cliente(total_pedidos=1, total_gasto=30.0, dias_desde_ultimo=5)
    assert calcular_segmento_rfm(c) == "novo"


def test_segmento_inativo_mais_90_dias():
    c = _cliente(total_pedidos=5, total_gasto=500.0, dias_desde_ultimo=91)
    assert calcular_segmento_rfm(c) == "inativo"


def test_segmento_campeao():
    c = _cliente(total_pedidos=5, total_gasto=201.0, dias_desde_ultimo=10)
    assert calcular_segmento_rfm(c) == "campeao"


def test_segmento_campeao_nao_sem_gasto_suficiente():
    c = _cliente(total_pedidos=5, total_gasto=150.0, dias_desde_ultimo=10)
    assert calcular_segmento_rfm(c) != "campeao"


def test_segmento_leal():
    c = _cliente(total_pedidos=4, total_gasto=120.0, dias_desde_ultimo=20)
    assert calcular_segmento_rfm(c) == "leal"


def test_segmento_em_risco():
    c = _cliente(total_pedidos=4, total_gasto=120.0, dias_desde_ultimo=50)
    assert calcular_segmento_rfm(c) == "em_risco"


def test_segmento_comum():
    c = _cliente(total_pedidos=2, total_gasto=40.0, dias_desde_ultimo=20)
    assert calcular_segmento_rfm(c) == "comum"


# ── limites de fronteira ─────────────────────────────────────────────────────

def test_segmento_inativo_exatamente_90_dias_nao_inativo():
    c = _cliente(total_pedidos=3, total_gasto=100.0, dias_desde_ultimo=90)
    assert calcular_segmento_rfm(c) != "inativo"


def test_segmento_leal_exatamente_30_dias():
    c = _cliente(total_pedidos=3, total_gasto=80.0, dias_desde_ultimo=30)
    assert calcular_segmento_rfm(c) == "leal"


def test_segmento_em_risco_exatamente_46_dias():
    c = _cliente(total_pedidos=3, total_gasto=80.0, dias_desde_ultimo=46)
    assert calcular_segmento_rfm(c) == "em_risco"
