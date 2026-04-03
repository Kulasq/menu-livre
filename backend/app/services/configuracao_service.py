from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.configuracao import Configuracao
from app.schemas.configuracao import ConfiguracaoUpdate, HorariosSchema

# Dias da semana em português (0=segunda, 6=domingo — padrão Python)
_DIAS = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]

# Fuso horário de Brasília (UTC-3)
BRT = timezone(timedelta(hours=-3))


def obter_configuracoes(db: Session) -> Configuracao:
    """Retorna a configuração da loja (sempre id=1). Cria com defaults se não existir."""
    config = db.get(Configuracao, 1)
    if not config:
        config = Configuracao(id=1, whatsapp="")
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def atualizar_configuracoes(dados: ConfiguracaoUpdate, db: Session) -> Configuracao:
    """Atualiza apenas os campos enviados. Cria o registro se não existir."""
    config = db.get(Configuracao, 1)
    if not config:
        config = Configuracao(id=1, whatsapp="")
        db.add(config)
        db.flush()

    campos = dados.model_dump(exclude_unset=True)

    # horarios vem como dict/HorariosSchema — serializa para JSON string
    if "horarios" in campos and campos["horarios"] is not None:
        horarios_val = campos.pop("horarios")
        if isinstance(horarios_val, dict):
            config.horarios_json = json.dumps(horarios_val)
        else:
            config.horarios_json = json.dumps(horarios_val.model_dump())
    elif "horarios" in campos:
        campos.pop("horarios")
        config.horarios_json = None

    for campo, valor in campos.items():
        setattr(config, campo, valor)

    db.commit()
    return db.get(Configuracao, 1)


def verificar_loja_aberta(config: Configuracao) -> bool:
    """
    Retorna True se a loja está aberta agora.
    Critérios (ambos precisam ser verdadeiros):
      1. aceitar_pedidos = True
      2. Horário atual (BRT) dentro de algum intervalo configurado para o dia
    Se não houver horários configurados, usa apenas aceitar_pedidos.
    """
    if not config.aceitar_pedidos:
        return False

    if not config.horarios_json:
        return config.aceitar_pedidos

    try:
        horarios_dict = json.loads(config.horarios_json)
    except (json.JSONDecodeError, TypeError):
        return config.aceitar_pedidos

    agora_brt = datetime.now(BRT)
    dia_semana = _DIAS[agora_brt.weekday()]  # segunda=0 ... domingo=6

    dia_config = horarios_dict.get(dia_semana)
    if not dia_config or not dia_config.get("aberto", False):
        return False

    hora_atual = agora_brt.hour * 60 + agora_brt.minute  # minutos desde meia-noite

    for intervalo in dia_config.get("horarios", []):
        inicio = _hhmm_para_minutos(intervalo.get("inicio", ""))
        fim = _hhmm_para_minutos(intervalo.get("fim", ""))
        if inicio is not None and fim is not None and inicio <= hora_atual <= fim:
            return True

    return False


def _hhmm_para_minutos(hhmm: str) -> int | None:
    """Converte 'HH:MM' para minutos desde meia-noite. Retorna None se inválido."""
    try:
        hora, minuto = hhmm.split(":")
        h, m = int(hora), int(minuto)
        if not (0 <= h <= 23) or not (0 <= m <= 59):
            return None
        return h * 60 + m
    except (ValueError, AttributeError):
        return None


def horarios_para_schema(config: Configuracao) -> HorariosSchema | None:
    """Converte horarios_json string → HorariosSchema para serialização."""
    if not config.horarios_json:
        return None
    try:
        return HorariosSchema(**json.loads(config.horarios_json))
    except Exception:
        return None
