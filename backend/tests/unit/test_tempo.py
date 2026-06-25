from __future__ import annotations
from datetime import date, datetime, timezone

from app.tempo import BRT_OFFSET, agora_utc, hoje_brt, inicio_dia_utc


def test_inicio_dia_utc_desloca_meia_noite_brt():
    """Meia-noite BRT de um dia == 03:00 UTC (naive) desse mesmo dia."""
    d = date(2026, 6, 25)
    assert inicio_dia_utc(d) == datetime(2026, 6, 25, 3, 0, 0)


def test_inicio_dia_utc_retorna_naive():
    """O resultado é naive para casar com `criado_em` (UTC naive no banco)."""
    assert inicio_dia_utc(date(2026, 1, 1)).tzinfo is None


def test_brt_offset_e_tres_horas():
    assert BRT_OFFSET.total_seconds() == 3 * 3600


def test_hoje_brt_bate_com_utc_menos_offset():
    esperado = (datetime.now(timezone.utc) - BRT_OFFSET).date()
    assert hoje_brt() == esperado


def test_agora_utc_e_aware_em_utc():
    agora = agora_utc()
    assert agora.tzinfo is not None
    assert agora.utcoffset().total_seconds() == 0
