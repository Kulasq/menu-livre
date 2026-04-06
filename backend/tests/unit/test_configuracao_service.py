from __future__ import annotations
import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.configuracao import Configuracao
from app.schemas.configuracao import ConfiguracaoUpdate, HorariosSchema, DiaHorario, HorarioIntervalo
from app.services.configuracao_service import (
    obter_configuracoes,
    atualizar_configuracoes,
    verificar_loja_aberta,
    horarios_para_schema,
    _hhmm_para_minutos,
    BRT,
)


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def configurar(conn, rec):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


# ── obter_configuracoes ───────────────────────────────────────────────────────

def test_obter_configuracoes_cria_se_nao_existir():
    db = setup_db()
    config = obter_configuracoes(db)
    assert config.id == 1
    assert config.nome_loja == "Pão de Mão"


def test_obter_configuracoes_retorna_existente():
    db = setup_db()
    db.add(Configuracao(id=1, whatsapp="81999990000", nome_loja="Teste"))
    db.commit()
    config = obter_configuracoes(db)
    assert config.nome_loja == "Teste"


# ── atualizar_configuracoes ───────────────────────────────────────────────────

def test_atualizar_campos_simples():
    db = setup_db()
    dados = ConfiguracaoUpdate(whatsapp="81999991111", taxa_entrega=5.0)
    config = atualizar_configuracoes(dados, db)
    assert config.whatsapp == "81999991111"
    assert config.taxa_entrega == 5.0


def test_atualizar_nao_sobrescreve_campo_nao_enviado():
    db = setup_db()
    db.add(Configuracao(id=1, whatsapp="81999990000", taxa_entrega=3.0))
    db.commit()
    dados = ConfiguracaoUpdate(nome_loja="Nova Loja")
    config = atualizar_configuracoes(dados, db)
    assert config.taxa_entrega == 3.0  # não foi enviado, deve manter
    assert config.nome_loja == "Nova Loja"


def test_atualizar_horarios_serializa_para_json():
    db = setup_db()
    horarios = HorariosSchema(
        domingo=DiaHorario(aberto=True, horarios=[HorarioIntervalo(inicio="19:00", fim="23:00")]),
        segunda=DiaHorario(aberto=True, horarios=[HorarioIntervalo(inicio="19:00", fim="23:00")]),
        terca=DiaHorario(aberto=False, horarios=[]),
        quarta=DiaHorario(aberto=False, horarios=[]),
        quinta=DiaHorario(aberto=False, horarios=[]),
        sexta=DiaHorario(aberto=True, horarios=[HorarioIntervalo(inicio="19:00", fim="23:00")]),
        sabado=DiaHorario(aberto=True, horarios=[HorarioIntervalo(inicio="19:00", fim="23:00")]),
    )
    dados = ConfiguracaoUpdate(horarios=horarios)
    config = atualizar_configuracoes(dados, db)
    assert config.horarios_json is not None
    parsed = json.loads(config.horarios_json)
    assert parsed["domingo"]["aberto"] is True
    assert parsed["terca"]["aberto"] is False


# ── verificar_loja_aberta ─────────────────────────────────────────────────────

def _config_com_horarios(aberto_flag: bool, dia: str, aberto_dia: bool, inicio: str, fim: str) -> Configuracao:
    """Helper: cria Configuracao com horários para um único dia."""
    dias = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
    horarios = {
        d: {"aberto": (d == dia and aberto_dia), "horarios": (
            [{"inicio": inicio, "fim": fim}] if d == dia and aberto_dia else []
        )}
        for d in dias
    }
    return Configuracao(
        id=1,
        whatsapp="",
        aceitar_pedidos=aberto_flag,
        horarios_json=json.dumps(horarios),
    )


def test_loja_fechada_por_flag():
    config = Configuracao(id=1, whatsapp="", aceitar_pedidos=False)
    assert verificar_loja_aberta(config) is False


def test_loja_aberta_sem_horarios_configurados():
    """Sem horarios_json, usa só o flag aceitar_pedidos."""
    config = Configuracao(id=1, whatsapp="", aceitar_pedidos=True, horarios_json=None)
    assert verificar_loja_aberta(config) is True


def test_loja_aberta_dentro_do_horario():
    # Simula uma segunda-feira às 20:00 BRT
    segunda_20h = datetime(2026, 3, 30, 23, 0, tzinfo=timezone.utc)  # 20:00 BRT = 23:00 UTC
    config = _config_com_horarios(True, "segunda", True, "19:00", "23:00")
    with patch("app.services.configuracao_service.datetime") as mock_dt:
        mock_dt.now.return_value = segunda_20h.astimezone(BRT)
        assert verificar_loja_aberta(config) is True


def test_loja_fechada_fora_do_horario():
    # Simula uma segunda-feira às 15:00 BRT (antes de abrir)
    segunda_15h = datetime(2026, 3, 30, 18, 0, tzinfo=timezone.utc)  # 15:00 BRT = 18:00 UTC
    config = _config_com_horarios(True, "segunda", True, "19:00", "23:00")
    with patch("app.services.configuracao_service.datetime") as mock_dt:
        mock_dt.now.return_value = segunda_15h.astimezone(BRT)
        assert verificar_loja_aberta(config) is False


def test_loja_fechada_dia_desabilitado():
    # Simula uma terça-feira — dia marcado como fechado
    terca_20h = datetime(2026, 3, 31, 23, 0, tzinfo=timezone.utc)  # 20:00 BRT
    config = _config_com_horarios(True, "segunda", True, "19:00", "23:00")  # só segunda aberta
    with patch("app.services.configuracao_service.datetime") as mock_dt:
        mock_dt.now.return_value = terca_20h.astimezone(BRT)
        assert verificar_loja_aberta(config) is False


# ── _hhmm_para_minutos ────────────────────────────────────────────────────────

def test_hhmm_para_minutos_valido():
    assert _hhmm_para_minutos("19:00") == 19 * 60
    assert _hhmm_para_minutos("23:30") == 23 * 60 + 30
    assert _hhmm_para_minutos("00:00") == 0


def test_hhmm_para_minutos_invalido():
    assert _hhmm_para_minutos("") is None
    assert _hhmm_para_minutos("abc") is None
    assert _hhmm_para_minutos("25:00") is None


# ── horarios_para_schema ──────────────────────────────────────────────────────

def test_horarios_para_schema_retorna_none_sem_json():
    config = Configuracao(id=1, whatsapp="", horarios_json=None)
    assert horarios_para_schema(config) is None


def test_horarios_para_schema_converte_corretamente():
    horarios = {
        "domingo": {"aberto": True, "horarios": [{"inicio": "19:00", "fim": "23:00"}]},
        "segunda": {"aberto": True, "horarios": [{"inicio": "19:00", "fim": "23:00"}]},
        "terca":   {"aberto": False, "horarios": []},
        "quarta":  {"aberto": False, "horarios": []},
        "quinta":  {"aberto": False, "horarios": []},
        "sexta":   {"aberto": True, "horarios": [{"inicio": "19:00", "fim": "23:00"}]},
        "sabado":  {"aberto": True, "horarios": [{"inicio": "19:00", "fim": "23:00"}]},
    }
    config = Configuracao(id=1, whatsapp="", horarios_json=json.dumps(horarios))
    schema = horarios_para_schema(config)
    assert schema is not None
    assert schema.domingo.aberto is True
    assert schema.terca.aberto is False
    assert schema.domingo.horarios[0].inicio == "19:00"


def test_horarios_para_schema_json_invalido_retorna_none():
    config = Configuracao(id=1, whatsapp="", horarios_json="{ isso nao e json valido }")
    assert horarios_para_schema(config) is None


# ── verificar_loja_aberta — edge cases ────────────────────────────────────────

def test_verificar_loja_aberta_json_invalido_usa_aceitar_pedidos():
    """JSON corrompido deve cair no fallback de aceitar_pedidos."""
    config = Configuracao(
        id=1, whatsapp="", aceitar_pedidos=True,
        horarios_json="{ json invalido }",
    )
    assert verificar_loja_aberta(config) is True


def test_verificar_loja_aberta_json_invalido_fechado_por_flag():
    config = Configuracao(
        id=1, whatsapp="", aceitar_pedidos=False,
        horarios_json="{ json invalido }",
    )
    assert verificar_loja_aberta(config) is False


def test_verificar_loja_aberta_exatamente_no_inicio_do_horario():
    """Loja deve estar aberta no minuto exato de abertura (início inclusivo)."""
    # segunda-feira às 19:00 BRT = 22:00 UTC; horário: 19:00–23:00
    segunda_19h = datetime(2026, 3, 30, 22, 0, tzinfo=timezone.utc)
    config = _config_com_horarios(True, "segunda", True, "19:00", "23:00")
    with patch("app.services.configuracao_service.datetime") as mock_dt:
        mock_dt.now.return_value = segunda_19h.astimezone(BRT)
        assert verificar_loja_aberta(config) is True


def test_verificar_loja_aberta_exatamente_no_fim_do_horario():
    """Loja deve estar aberta no minuto exato de encerramento (fim inclusivo)."""
    # segunda-feira às 23:00 BRT = 02:00 UTC (+1 dia)
    segunda_23h = datetime(2026, 3, 31, 2, 0, tzinfo=timezone.utc)
    config = _config_com_horarios(True, "segunda", True, "19:00", "23:00")
    with patch("app.services.configuracao_service.datetime") as mock_dt:
        mock_dt.now.return_value = segunda_23h.astimezone(BRT)
        assert verificar_loja_aberta(config) is True


def test_verificar_loja_aberta_um_minuto_apos_fechamento():
    """Um minuto após o horário de fechamento deve retornar False."""
    # segunda-feira às 23:01 BRT
    segunda_23h01 = datetime(2026, 3, 31, 2, 1, tzinfo=timezone.utc)
    config = _config_com_horarios(True, "segunda", True, "19:00", "23:00")
    with patch("app.services.configuracao_service.datetime") as mock_dt:
        mock_dt.now.return_value = segunda_23h01.astimezone(BRT)
        assert verificar_loja_aberta(config) is False


# ── _hhmm_para_minutos — edge cases ──────────────────────────────────────────

def test_hhmm_para_minutos_23_59_valido():
    assert _hhmm_para_minutos("23:59") == 23 * 60 + 59


def test_hhmm_para_minutos_60_minutos_invalido():
    assert _hhmm_para_minutos("12:60") is None


def test_hhmm_para_minutos_24_horas_invalido():
    assert _hhmm_para_minutos("24:00") is None


def test_hhmm_para_minutos_valor_negativo_invalido():
    assert _hhmm_para_minutos("-1:00") is None


# ── atualizar_configuracoes — horarios=None limpa JSON ───────────────────────

def test_atualizar_horarios_none_limpa_horarios_json():
    db = setup_db()
    # Primeiro, define um horário
    horarios = HorariosSchema(
        domingo=DiaHorario(aberto=True, horarios=[HorarioIntervalo(inicio="19:00", fim="23:00")]),
        segunda=DiaHorario(aberto=False, horarios=[]),
        terca=DiaHorario(aberto=False, horarios=[]),
        quarta=DiaHorario(aberto=False, horarios=[]),
        quinta=DiaHorario(aberto=False, horarios=[]),
        sexta=DiaHorario(aberto=False, horarios=[]),
        sabado=DiaHorario(aberto=False, horarios=[]),
    )
    atualizar_configuracoes(ConfiguracaoUpdate(horarios=horarios), db)

    # Depois, envia horarios=None para limpar
    config = atualizar_configuracoes(ConfiguracaoUpdate(horarios=None), db)
    assert config.horarios_json is None
