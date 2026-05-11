from __future__ import annotations
from pydantic import BaseModel, Field, field_validator, model_validator
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
    tipo: str = Field(pattern="^(delivery|retirada|balcao)$")
    endereco_entrega: str | None = None
    metodo_pagamento: str = Field(pattern="^(pix|dinheiro|cartao)$")
    troco_para: float | None = Field(default=None, gt=0)
    observacao: str | None = None
    agendado_para: datetime | None = None
    cupom_codigo: str | None = None
    itens: list[PedidoItemCreate] = Field(min_length=1)

    @model_validator(mode='after')
    def validar_troco(self) -> 'PedidoCreate':
        if self.metodo_pagamento != 'dinheiro':
            self.troco_para = None
        return self


class PedidoStatusUpdate(BaseModel):
    status: str = Field(
        pattern="^(confirmado|em_preparo|pronto|entregue|cancelado)$"
    )


class PedidoPagamentoUpdate(BaseModel):
    status_pagamento: str = Field(pattern="^(pendente|pago)$")


class PedidoItemModificadorResponse(BaseModel):
    id: int
    modificador_id: int | None
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
    telefone: str | None

    model_config = {"from_attributes": True}


class PedidoResponse(BaseModel):
    id: int
    numero: str
    cliente: PedidoClienteResponse | None
    tipo: str
    status: str
    endereco_entrega: str | None
    subtotal: float
    taxa_entrega: float
    desconto_cupom: float = 0.0
    cupom_codigo: str | None = None
    total: float
    metodo_pagamento: str | None
    troco_para: float | None
    status_pagamento: str
    observacao: str | None
    nome_cliente_balcao: str | None = None
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
    pix_br_code: str | None = None
    pix_qr_code_base64: str | None = None


class PedidoAdminCreate(BaseModel):
    """Schema para criação de pedido pelo painel admin.

    Diferenças do PedidoCreate público:
    - Aceita cliente_id (existente) OU cliente_telefone + cliente_nome (novo cliente)
      OU nenhum (cria/reutiliza cliente sistema 'Balcão')
    - metodo_pagamento opcional (pode ser definido depois)
    - Bypassa validações de horário/agendamento
    - Não gera URL WhatsApp
    """
    tipo: str = Field(pattern="^(delivery|retirada|balcao)$")
    endereco_entrega: str | None = None
    metodo_pagamento: str | None = None
    troco_para: float | None = Field(default=None, gt=0)
    observacao: str | None = None
    cupom_codigo: str | None = None
    itens: list[PedidoItemCreate] = Field(min_length=1)
    cliente_id: int | None = None
    cliente_telefone: str | None = None
    cliente_nome: str | None = None
    nome_cliente_balcao: str | None = None   # nome opcional para pedidos de balcão

    @model_validator(mode='after')
    def validar_pagamento_e_troco(self) -> 'PedidoAdminCreate':
        if self.metodo_pagamento and self.metodo_pagamento not in ('pix', 'dinheiro', 'cartao'):
            raise ValueError("metodo_pagamento deve ser pix, dinheiro ou cartao.")
        if self.metodo_pagamento != 'dinheiro':
            self.troco_para = None
        return self


class PedidoAdminResponse(BaseModel):
    pedido: PedidoResponse