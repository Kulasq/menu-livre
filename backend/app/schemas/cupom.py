from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import Literal


TipoCupom = Literal["percentual", "valor_fixo", "frete_gratis", "brinde"]


class CupomCreate(BaseModel):
    codigo: str = Field(min_length=2, max_length=50)
    tipo: TipoCupom
    valor: float = Field(default=0.0, ge=0)
    desconto_maximo: float | None = Field(default=None, gt=0)
    produto_brinde_id: int | None = None
    valor_minimo_pedido: float = Field(default=0.0, ge=0)
    limite_total_usos: int | None = Field(default=None, gt=0)
    limite_por_cliente: int = Field(default=0, ge=0)
    somente_primeira_compra: bool = False
    data_inicio: datetime | None = None
    data_fim: datetime | None = None
    ativo: bool = True

    @field_validator("codigo")
    @classmethod
    def normalizar_codigo(cls, v: str) -> str:
        return v.strip().upper()


class CupomUpdate(BaseModel):
    codigo: str | None = Field(default=None, min_length=2, max_length=50)
    tipo: TipoCupom | None = None
    valor: float | None = Field(default=None, ge=0)
    desconto_maximo: float | None = None
    produto_brinde_id: int | None = None
    valor_minimo_pedido: float | None = Field(default=None, ge=0)
    limite_total_usos: int | None = None
    limite_por_cliente: int | None = Field(default=None, ge=0)
    somente_primeira_compra: bool | None = None
    data_inicio: datetime | None = None
    data_fim: datetime | None = None
    ativo: bool | None = None

    @field_validator("codigo")
    @classmethod
    def normalizar_codigo(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else v


class ProdutoBrindeResponse(BaseModel):
    id: int
    nome: str

    model_config = {"from_attributes": True}


class CupomResponse(BaseModel):
    id: int
    codigo: str
    tipo: str
    valor: float
    desconto_maximo: float | None
    produto_brinde_id: int | None
    produto_brinde: ProdutoBrindeResponse | None = None
    valor_minimo_pedido: float
    limite_total_usos: int | None
    usos_atuais: int
    limite_por_cliente: int
    somente_primeira_compra: bool
    data_inicio: datetime | None
    data_fim: datetime | None
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime
    # Campos calculados (agregados de CupomUso) — opcionais na listagem
    faturamento_gerado: float | None = None
    ultimo_uso: datetime | None = None

    model_config = {"from_attributes": True}

    @field_validator("data_inicio", "data_fim", "criado_em", "atualizado_em", "ultimo_uso", mode="before")
    @classmethod
    def assume_utc(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class CupomUsoResponse(BaseModel):
    id: int
    cupom_id: int
    pedido_id: int
    cliente_telefone: str | None
    desconto_aplicado: float
    subtotal_pedido: float
    criado_em: datetime

    model_config = {"from_attributes": True}

    @field_validator("criado_em", mode="before")
    @classmethod
    def assume_utc(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


# ── Preview de validação (retornado para o checkout antes de finalizar) ──────

class CupomValidarRequest(BaseModel):
    codigo: str
    subtotal: float = Field(ge=0)
    telefone: str | None = None

    @field_validator("codigo")
    @classmethod
    def normalizar_codigo(cls, v: str) -> str:
        return v.strip().upper()


class CupomValidacaoResponse(BaseModel):
    valido: bool
    # Valor em R$ a descontar do subtotal
    desconto: float = 0.0
    # True se o cupom zera a taxa de entrega
    frete_gratis: bool = False
    # Se tipo=brinde, traz o produto
    produto_brinde_id: int | None = None
    produto_brinde_nome: str | None = None
    # Mensagem de erro para o cliente (genérica, não revela se código existe)
    motivo: str | None = None
    # Para exibição no checkout: total_com_desconto = subtotal - desconto
    total_com_desconto: float = 0.0
