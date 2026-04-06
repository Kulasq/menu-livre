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

    Prioridade:
      1. fechado_manualmente=True  → sempre False (override manual)
      2. Sem horarios_json         → True (sem agenda = sempre aberta)
      3. Com horarios_json         → verifica horário BRT atual contra a agenda
    """
    if config.fechado_manualmente:
        return False

    if not config.horarios_json:
        return True  # sem agenda configurada = loja aberta por padrão

    try:
        horarios_dict = json.loads(config.horarios_json)
    except (json.JSONDecodeError, TypeError):
        return True  # JSON corrompido: não bloquear a loja

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


def calcular_proxima_abertura(config: Configuracao) -> datetime | None:
    """
    Retorna o datetime (BRT) do próximo horário de abertura configurado.
    Percorre os próximos 7 dias. Retorna None se não encontrar.
    """
    if not config.horarios_json:
        return None

    try:
        horarios_dict = json.loads(config.horarios_json)
    except (json.JSONDecodeError, TypeError):
        return None

    agora_brt = datetime.now(BRT)
    hora_atual_min = agora_brt.hour * 60 + agora_brt.minute

    for dias_afrente in range(8):  # hoje + próximos 7 dias
        data_check = agora_brt + timedelta(days=dias_afrente)
        dia_semana = _DIAS[data_check.weekday()]
        dia_config = horarios_dict.get(dia_semana)

        if not dia_config or not dia_config.get("aberto", False):
            continue

        for intervalo in dia_config.get("horarios", []):
            inicio_min = _hhmm_para_minutos(intervalo.get("inicio", ""))
            if inicio_min is None:
                continue

            # Se for hoje, só considerar horários ainda não chegados
            if dias_afrente == 0 and inicio_min <= hora_atual_min:
                continue

            return data_check.replace(
                hour=inicio_min // 60,
                minute=inicio_min % 60,
                second=0,
                microsecond=0,
            )

    return None


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
