from __future__ import annotations
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


# ── Horários ──────────────────────────────────────────────────────────────────

class HorarioIntervalo(BaseModel):
    inicio: str  # "19:00"
    fim: str     # "23:00"

    @field_validator("inicio", "fim")
    @classmethod
    def validar_formato(cls, v: str) -> str:
        partes = v.split(":")
        if len(partes) != 2:
            raise ValueError("Horário deve estar no formato HH:MM")
        hora, minuto = partes
        if not hora.isdigit() or not minuto.isdigit():
            raise ValueError("Horário deve estar no formato HH:MM")
        if not (0 <= int(hora) <= 23) or not (0 <= int(minuto) <= 59):
            raise ValueError("Hora ou minuto fora do intervalo permitido")
        return v


class DiaHorario(BaseModel):
    aberto: bool
    horarios: list[HorarioIntervalo] = []


class HorariosSchema(BaseModel):
    domingo: DiaHorario
    segunda: DiaHorario
    terca: DiaHorario
    quarta: DiaHorario
    quinta: DiaHorario
    sexta: DiaHorario
    sabado: DiaHorario


# ── Configuração admin ────────────────────────────────────────────────────────

class ConfiguracaoUpdate(BaseModel):
    """Todos os campos opcionais — atualiza só o que for enviado."""
    nome_loja: Optional[str] = None
    whatsapp: Optional[str] = None
    chave_pix: Optional[str] = None
    tipo_chave_pix: Optional[str] = None
    taxa_entrega: Optional[float] = None
    pedido_minimo: Optional[float] = None
    tempo_entrega_min: Optional[int] = None
    tempo_entrega_max: Optional[int] = None
    fechado_manualmente: Optional[bool] = None
    aceitar_agendamentos: Optional[bool] = None
    limite_agendamentos: Optional[int] = None
    mensagem_fechado: Optional[str] = None
    instagram_url: Optional[str] = None
    horarios: Optional[HorariosSchema] = None
    # Aparência
    cor_primaria: Optional[str] = None
    cor_secundaria: Optional[str] = None
    cor_fundo: Optional[str] = None
    cor_fonte: Optional[str] = None
    cor_banner: Optional[str] = None


class ConfiguracaoResponse(BaseModel):
    """Resposta completa para o painel admin."""
    id: int
    nome_loja: str
    logo_url: Optional[str]
    banner_url: Optional[str]
    whatsapp: str
    chave_pix: Optional[str]
    tipo_chave_pix: Optional[str]
    taxa_entrega: float
    pedido_minimo: float
    tempo_entrega_min: int
    tempo_entrega_max: int
    fechado_manualmente: bool
    aceitar_agendamentos: bool
    limite_agendamentos: int
    mensagem_fechado: str
    instagram_url: Optional[str]
    horarios: Optional[HorariosSchema]
    atualizado_em: datetime
    # Aparência
    cor_primaria: Optional[str]
    cor_secundaria: Optional[str]
    cor_fundo: Optional[str]
    cor_fonte: Optional[str]
    cor_banner: Optional[str]

    model_config = {"from_attributes": True}


# ── Configuração pública ──────────────────────────────────────────────────────

class ConfiguracaoPublicaResponse(BaseModel):
    """Resposta para o cardápio público — inclui status calculado da loja."""
    nome_loja: str
    logo_url: Optional[str]
    banner_url: Optional[str]
    whatsapp: str
    chave_pix: Optional[str]
    taxa_entrega: float
    pedido_minimo: float
    tempo_entrega_min: int
    tempo_entrega_max: int
    aceitar_agendamentos: bool
    mensagem_fechado: str
    instagram_url: Optional[str]
    horarios: Optional[HorariosSchema]
    aberto: bool          # calculado em tempo real pelo service
    fechado_manualmente: bool  # para o frontend distinguir tipo de fechamento
    proxima_abertura: Optional[str]  # "HH:MM" do próximo horário de abertura, ou None
    # Aparência
    cor_primaria: Optional[str]
    cor_secundaria: Optional[str]
    cor_fundo: Optional[str]
    cor_fonte: Optional[str]
    cor_banner: Optional[str]
