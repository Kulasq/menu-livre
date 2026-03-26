from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime


# ── Categorias ───────────────────────────────────────────────────────────────

class CategoriaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    descricao: str | None = None
    ordem: int = 0


class CategoriaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=100)
    descricao: str | None = None
    ordem: int | None = None
    ativo: bool | None = None


class CategoriaResponse(BaseModel):
    id: int
    nome: str
    descricao: str | None
    ordem: int
    ativo: bool

    model_config = {"from_attributes": True}


# ── Modificadores ─────────────────────────────────────────────────────────────

class ModificadorCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    preco_adicional: float = 0.0
    disponivel: bool = True
    ordem: int = 0


class ModificadorResponse(BaseModel):
    id: int
    nome: str
    preco_adicional: float
    disponivel: bool
    ordem: int

    model_config = {"from_attributes": True}


class GrupoModificadorCreate(BaseModel):
    produto_id: int | None = None
    nome: str = Field(min_length=2, max_length=100)
    obrigatorio: bool = False
    selecao_minima: int = 0
    selecao_maxima: int = 1
    ordem: int = 0
    modificadores: list[ModificadorCreate] = []


class GrupoModificadorResponse(BaseModel):
    id: int
    produto_id: int | None
    nome: str
    obrigatorio: bool
    selecao_minima: int
    selecao_maxima: int
    ordem: int
    modificadores: list[ModificadorResponse] = []

    model_config = {"from_attributes": True}


# ── Produtos ──────────────────────────────────────────────────────────────────

class ProdutoCreate(BaseModel):
    categoria_id: int
    nome: str = Field(min_length=2, max_length=150)
    descricao: str | None = None
    preco: float = Field(gt=0)
    disponivel: bool = True
    destaque: bool = False
    ordem: int = 0


class ProdutoUpdate(BaseModel):
    categoria_id: int | None = None
    nome: str | None = Field(default=None, min_length=2)
    descricao: str | None = None
    preco: float | None = Field(default=None, gt=0)
    disponivel: bool | None = None
    destaque: bool | None = None
    ordem: int | None = None


class ProdutoResponse(BaseModel):
    id: int
    categoria_id: int
    nome: str
    descricao: str | None
    preco: float
    foto_url: str | None
    disponivel: bool
    destaque: bool
    ordem: int
    grupos_modificadores: list[GrupoModificadorResponse] = []

    model_config = {"from_attributes": True}


# ── Cardápio público ──────────────────────────────────────────────────────────

class CardapioCategoriaResponse(BaseModel):
    id: int
    nome: str
    descricao: str | None
    ordem: int
    produtos: list[ProdutoResponse] = []

    model_config = {"from_attributes": True}


class CardapioPublicoResponse(BaseModel):
    categorias: list[CardapioCategoriaResponse]
    destaques: list[ProdutoResponse]