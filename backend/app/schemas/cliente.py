from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime


class ClienteIdentificar(BaseModel):
    telefone: str
    nome: str | None = None


class ClienteUpdate(BaseModel):
    nome: str | None = None
    endereco_padrao: str | None = None


class ClienteResponse(BaseModel):
    id: int
    nome: str
    telefone: str | None
    endereco_padrao: str | None
    total_pedidos: int
    segmento: str
    criado_em: datetime

    model_config = {"from_attributes": True}


class ClienteSessionResponse(BaseModel):
    cliente: ClienteResponse
    access_token: str
    token_type: str = "bearer"


class EnderecoResponse(BaseModel):
    id: int
    cliente_id: int
    endereco: str
    criado_em: datetime

    model_config = {"from_attributes": True}


class ClienteAdminUpdate(BaseModel):
    nome: str | None = None
    telefone: str | None = None


class EnderecoCreate(BaseModel):
    endereco: str


class ClienteAdminListItem(BaseModel):
    id: int
    nome: str
    telefone: str | None
    total_pedidos: int
    total_gasto: float
    ultimo_pedido: datetime | None
    segmento: str

    model_config = {"from_attributes": True}


class ClienteAdminListResponse(BaseModel):
    clientes: list[ClienteAdminListItem]
    total: int


class ClienteAdminDetalhe(BaseModel):
    id: int
    nome: str
    telefone: str | None
    endereco_padrao: str | None
    total_pedidos: int
    total_gasto: float
    ultimo_pedido: datetime | None
    segmento: str
    pontos: int
    nivel_fidelidade: str
    criado_em: datetime

    model_config = {"from_attributes": True}