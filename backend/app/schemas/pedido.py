from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone


class PedidoItemModificadorCreate(BaseModel):
    modificador_id: int


class PedidoItemCreate(BaseModel):
    produto_id: int | None = None
    variante_id: int | None = None
    quantidade: int = Field(default=1, ge=1)
    observacao: str | None = None
    modificadores: list[PedidoItemModificadorCreate] = []


class PedidoCreate(BaseModel):
    tipo: str = Field(pattern="^(delivery|retirada)$")
    endereco_entrega: str | None = None
    metodo_pagamento: str = Field(pattern="^(pix|dinheiro|cartao)$")
    observacao: str | None = None
    agendado_para: datetime | None = None
    itens: list[PedidoItemCreate] = Field(min_length=1)


class PedidoStatusUpdate(BaseModel):
    status: str = Field(
        pattern="^(confirmado|em_preparo|pronto|entregue|cancelado)$"
    )


class PedidoPagamentoUpdate(BaseModel):
    status_pagamento: str = Field(pattern="^(pendente|pago)$")


class PedidoItemModificadorResponse(BaseModel):
    id: int
    modificador_id: int
    nome_snapshot: str
    preco_snapshot: float

    model_config = {"from_attributes": True}


class PedidoItemResponse(BaseModel):
    id: int
    produto_id: int | None
    variante_id: int | None
    nome_snapshot: str
    preco_snapshot: float
    quantidade: int
    subtotal: float
    observacao: str | None
    modificadores: list[PedidoItemModificadorResponse] = []

    model_config = {"from_attributes": True}


class PedidoClienteResponse(BaseModel):
    id: int
    nome: str
    telefone: str

    model_config = {"from_attributes": True}


class PedidoResponse(BaseModel):
    id: int
    numero: str
    cliente: PedidoClienteResponse
    tipo: str
    status: str
    endereco_entrega: str | None
    subtotal: float
    taxa_entrega: float
    total: float
    metodo_pagamento: str | None
    status_pagamento: str
    observacao: str | None
    agendado_para: datetime | None
    criado_em: datetime
    itens: list[PedidoItemResponse] = []

    model_config = {"from_attributes": True}

    @field_validator('agendado_para', 'criado_em', mode='before')
    @classmethod
    def assume_utc(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class NovoPedidoResponse(BaseModel):
    pedido: PedidoResponse
    mensagem_whatsapp: str
    whatsapp_url: str