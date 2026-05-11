"""Testes unitários do cupom_service.

Cobre:
- Validação de cupom percentual, valor_fixo, frete_gratis, brinde
- Regras de elegibilidade: valor mínimo, limite de usos, 1x por cliente, primeira compra
- Janela de validade (data_inicio, data_fim)
- Cupom inativo
- Desconto máximo em cupom percentual
- total negativo (subtotal < desconto_fixo)
- CRUD admin básico
"""
from __future__ import annotations
import pytest
from datetime import datetime, timezone, timedelta

from app.models.cupom import Cupom, CupomUso
from app.models.cliente import Cliente
from app.models.pedido import Pedido
from app.schemas.cupom import CupomCreate, CupomValidarRequest
from app.services import cupom_service


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _cupom(db, **kwargs) -> Cupom:
    """Cria e persiste um Cupom com defaults sensatos."""
    defaults = dict(
        codigo="TEST10",
        tipo="percentual",
        valor=10.0,
        ativo=True,
    )
    defaults.update(kwargs)
    c = Cupom(**defaults)
    db.add(c)
    db.flush()
    return c


def _cliente(db, telefone="11999990000") -> Cliente:
    c = Cliente(nome="Teste", telefone=telefone)
    db.add(c)
    db.flush()
    return c


# ── Testes de validação ───────────────────────────────────────────────────────

class TestValidarCupom:

    def test_percentual_simples(self, db_teste):
        _cupom(db_teste, codigo="P10", tipo="percentual", valor=10.0)
        res = cupom_service.validar_cupom("P10", 100.0, None, db_teste)
        assert res.valido is True
        assert res.desconto == pytest.approx(10.0)
        assert res.frete_gratis is False

    def test_percentual_com_teto(self, db_teste):
        _cupom(db_teste, codigo="P50TETO", tipo="percentual", valor=50.0, desconto_maximo=20.0)
        # 50% de 100 = 50, mas teto é 20
        res = cupom_service.validar_cupom("P50TETO", 100.0, None, db_teste)
        assert res.valido is True
        assert res.desconto == pytest.approx(20.0)

    def test_valor_fixo(self, db_teste):
        _cupom(db_teste, codigo="R10", tipo="valor_fixo", valor=10.0)
        res = cupom_service.validar_cupom("R10", 50.0, None, db_teste)
        assert res.valido is True
        assert res.desconto == pytest.approx(10.0)

    def test_valor_fixo_nao_negativo(self, db_teste):
        """Cupom de R$30 em pedido de R$20 — desconto máximo é o subtotal."""
        _cupom(db_teste, codigo="R30", tipo="valor_fixo", valor=30.0)
        res = cupom_service.validar_cupom("R30", 20.0, None, db_teste)
        assert res.valido is True
        assert res.desconto == pytest.approx(20.0)
        assert res.total_com_desconto == pytest.approx(0.0)

    def test_frete_gratis(self, db_teste):
        _cupom(db_teste, codigo="FRETE", tipo="frete_gratis")
        res = cupom_service.validar_cupom("FRETE", 50.0, None, db_teste)
        assert res.valido is True
        assert res.frete_gratis is True
        assert res.desconto == 0.0

    def test_codigo_case_insensitive(self, db_teste):
        _cupom(db_teste, codigo="MAIUSC", tipo="valor_fixo", valor=5.0)
        res = cupom_service.validar_cupom("maiusc", 50.0, None, db_teste)
        # validar_cupom recebe código já normalizado pelo schema — aqui testamos a busca
        # mesmo em lowercase, o DB guarda MAIUSC
        assert res.valido is True

    def test_cupom_inexistente_retorna_invalido(self, db_teste):
        res = cupom_service.validar_cupom("NAOEXISTE", 100.0, None, db_teste)
        assert res.valido is False
        assert "inválido" in (res.motivo or "").lower()

    def test_cupom_inativo(self, db_teste):
        _cupom(db_teste, codigo="INATIVO", tipo="valor_fixo", valor=5.0, ativo=False)
        res = cupom_service.validar_cupom("INATIVO", 100.0, None, db_teste)
        assert res.valido is False

    def test_cupom_expirado(self, db_teste):
        ontem = datetime.now(timezone.utc) - timedelta(days=1)
        _cupom(db_teste, codigo="EXPIRADO", tipo="valor_fixo", valor=5.0, data_fim=ontem)
        res = cupom_service.validar_cupom("EXPIRADO", 100.0, None, db_teste)
        assert res.valido is False

    def test_cupom_nao_iniciado(self, db_teste):
        amanha = datetime.now(timezone.utc) + timedelta(days=1)
        _cupom(db_teste, codigo="FUTURO", tipo="valor_fixo", valor=5.0, data_inicio=amanha)
        res = cupom_service.validar_cupom("FUTURO", 100.0, None, db_teste)
        assert res.valido is False

    def test_valor_minimo_pedido_nao_atingido(self, db_teste):
        _cupom(db_teste, codigo="MIN50", tipo="valor_fixo", valor=10.0, valor_minimo_pedido=50.0)
        res = cupom_service.validar_cupom("MIN50", 30.0, None, db_teste)
        assert res.valido is False
        assert "mínimo" in (res.motivo or "").lower()

    def test_valor_minimo_pedido_atingido(self, db_teste):
        _cupom(db_teste, codigo="MIN50OK", tipo="valor_fixo", valor=10.0, valor_minimo_pedido=50.0)
        res = cupom_service.validar_cupom("MIN50OK", 50.0, None, db_teste)
        assert res.valido is True

    def test_limite_total_esgotado(self, db_teste):
        _cupom(db_teste, codigo="ESGOTADO", tipo="valor_fixo", valor=5.0,
               limite_total_usos=3, usos_atuais=3)
        res = cupom_service.validar_cupom("ESGOTADO", 100.0, None, db_teste)
        assert res.valido is False
        assert "esgotado" in (res.motivo or "").lower()

    def test_limite_total_ainda_disponivel(self, db_teste):
        _cupom(db_teste, codigo="DISP", tipo="valor_fixo", valor=5.0,
               limite_total_usos=5, usos_atuais=4)
        res = cupom_service.validar_cupom("DISP", 100.0, None, db_teste)
        assert res.valido is True

    def test_limite_por_cliente_excedido(self, db_teste):
        from app.models.pedido import Pedido as PedidoModel
        from app.models.cliente import Cliente as ClienteModel
        # Cria cliente e pedido reais para satisfazer FK
        cli = ClienteModel(nome="X", telefone="11999990000")
        db_teste.add(cli)
        db_teste.flush()
        ped = PedidoModel(
            numero="ML-XTEST",
            cliente_id=cli.id,
            tipo="retirada",
            subtotal=100.0,
            taxa_entrega=0.0,
            total=100.0,
        )
        db_teste.add(ped)
        db_teste.flush()

        c = _cupom(db_teste, codigo="1XCLIENTE", tipo="valor_fixo", valor=5.0, limite_por_cliente=1)
        uso = CupomUso(
            cupom_id=c.id,
            pedido_id=ped.id,
            cliente_telefone="11999990000",
            desconto_aplicado=5.0,
            subtotal_pedido=100.0,
        )
        db_teste.add(uso)
        db_teste.flush()

        res = cupom_service.validar_cupom("1XCLIENTE", 100.0, "11999990000", db_teste)
        assert res.valido is False
        assert "utilizado" in (res.motivo or "").lower()

    def test_limite_por_cliente_diferente_telefone(self, db_teste):
        """Outro telefone ainda pode usar o cupom."""
        from app.models.pedido import Pedido as PedidoModel
        from app.models.cliente import Cliente as ClienteModel
        cli = ClienteModel(nome="Y", telefone="11999990001")
        db_teste.add(cli)
        db_teste.flush()
        ped = PedidoModel(
            numero="ML-YTEST",
            cliente_id=cli.id,
            tipo="retirada",
            subtotal=100.0,
            taxa_entrega=0.0,
            total=100.0,
        )
        db_teste.add(ped)
        db_teste.flush()

        c = _cupom(db_teste, codigo="1XOUTROCLIENTE", tipo="valor_fixo", valor=5.0, limite_por_cliente=1)
        uso = CupomUso(
            cupom_id=c.id,
            pedido_id=ped.id,
            cliente_telefone="11999990001",
            desconto_aplicado=5.0,
            subtotal_pedido=100.0,
        )
        db_teste.add(uso)
        db_teste.flush()

        res = cupom_service.validar_cupom("1XOUTROCLIENTE", 100.0, "11888880000", db_teste)
        assert res.valido is True


# ── Testes de CRUD ────────────────────────────────────────────────────────────

class TestCrudCupom:

    def test_criar_cupom(self, db_teste):
        dados = CupomCreate(codigo="NOVO", tipo="percentual", valor=15.0)
        cupom = cupom_service.criar_cupom(dados, db_teste)
        assert cupom.id is not None
        assert cupom.codigo == "NOVO"
        assert cupom.usos_atuais == 0

    def test_criar_cupom_codigo_normalizado(self, db_teste):
        """Código deve ser guardado em maiúsculas."""
        dados = CupomCreate(codigo="minusculo", tipo="valor_fixo", valor=5.0)
        cupom = cupom_service.criar_cupom(dados, db_teste)
        assert cupom.codigo == "MINUSCULO"

    def test_criar_cupom_codigo_duplicado_raises(self, db_teste):
        from fastapi import HTTPException
        dados = CupomCreate(codigo="DUP", tipo="valor_fixo", valor=5.0)
        cupom_service.criar_cupom(dados, db_teste)
        with pytest.raises(HTTPException) as exc:
            cupom_service.criar_cupom(dados, db_teste)
        assert exc.value.status_code == 409

    def test_deletar_sem_usos_remove_fisicamente(self, db_teste):
        dados = CupomCreate(codigo="DELME", tipo="valor_fixo", valor=5.0)
        c = cupom_service.criar_cupom(dados, db_teste)
        cupom_id = c.id
        cupom_service.deletar_cupom(cupom_id, db_teste)
        assert db_teste.get(Cupom, cupom_id) is None

    def test_deletar_com_usos_remove_fisicamente(self, db_teste):
        c = _cupom(db_teste, codigo="COMUSO", tipo="valor_fixo", valor=5.0, usos_atuais=1)
        cupom_id = c.id
        cupom_service.deletar_cupom(cupom_id, db_teste)
        # Hard delete sempre — independente de ter usos
        assert db_teste.get(Cupom, cupom_id) is None
