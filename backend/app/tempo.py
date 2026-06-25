from __future__ import annotations
from datetime import datetime, date, time, timedelta, timezone

# Fuso de Brasília centralizado. O Brasil não tem mais horário de verão (extinto
# em 2019), então um offset fixo UTC-3 é suficiente e evita depender do tz db.
# `criado_em` e demais timestamps são gravados em UTC; estas funções alinham os
# limites de data ao dia civil brasileiro sem espalhar `timedelta(hours=3)` pelo
# código.
BRT_OFFSET = timedelta(hours=3)


def agora_utc() -> datetime:
    """Instante atual em UTC (aware). Usar para timestamps persistidos."""
    return datetime.now(timezone.utc)


def hoje_brt() -> date:
    """Data de 'hoje' no fuso de Brasília (UTC-3)."""
    return (datetime.now(timezone.utc) - BRT_OFFSET).date()


def inicio_dia_utc(dia: date) -> datetime:
    """Meia-noite local (BRT) de `dia`, expressa como UTC naive.

    Como `criado_em` é armazenado em UTC naive, comparar com este valor alinha o
    filtro ao dia civil brasileiro (00:00 BRT == 03:00 UTC).
    """
    return datetime.combine(dia, time.min) + BRT_OFFSET
