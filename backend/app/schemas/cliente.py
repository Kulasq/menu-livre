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
    telefone: str
    endereco_padrao: str | None
    total_pedidos: int
    segmento: str
    criado_em: datetime

    model_config = {"from_attributes": True}


class ClienteSessionResponse(BaseModel):
    cliente: ClienteResponse
    access_token: str
    token_type: str = "bearer"