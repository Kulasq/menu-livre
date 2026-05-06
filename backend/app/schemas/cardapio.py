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
    controle_estoque: bool = False
    estoque_atual: int = Field(default=0, ge=0)
    estoque_minimo: int = Field(default=0, ge=0)
    ordem: int = 0


class ModificadorUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    preco_adicional: float | None = None
    disponivel: bool | None = None
    controle_estoque: bool | None = None
    estoque_atual: int | None = Field(default=None, ge=0)
    estoque_minimo: int | None = Field(default=None, ge=0)
    ordem: int | None = None


class ModificadorResponse(BaseModel):
    id: int
    nome: str
    preco_adicional: float
    disponivel: bool
    controle_estoque: bool
    estoque_atual: int
    estoque_minimo: int
    ordem: int

    model_config = {"from_attributes": True}


class GrupoModificadorCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    obrigatorio: bool = False
    selecao_minima: int = 0
    selecao_maxima: int = 1
    ativo: bool = True
    modificadores: list[ModificadorCreate] = []


class GrupoModificadorUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=100)
    obrigatorio: bool | None = None
    selecao_minima: int | None = None
    selecao_maxima: int | None = None
    ativo: bool | None = None


class GrupoModificadorResponse(BaseModel):
    id: int
    nome: str
    obrigatorio: bool
    selecao_minima: int
    selecao_maxima: int
    ativo: bool = True
    modificadores: list[ModificadorResponse] = []

    model_config = {"from_attributes": True}


class GrupoModificadorAdminResponse(GrupoModificadorResponse):
    """Resposta usada na listagem da seção de grupos — inclui contagem de produtos."""
    total_produtos: int = 0


# ── Vincular grupo a produtos ─────────────────────────────────────────────────

class VincularGrupoRequest(BaseModel):
    modo: str = Field(pattern="^(todos|categoria|produtos)$")
    categoria_id: int | None = None
    produtos_ids: list[int] = []


# ── Produtos ──────────────────────────────────────────────────────────────────

class ProdutoCreate(BaseModel):
    categoria_id: int
    nome: str = Field(min_length=2, max_length=150)
    descricao: str | None = None
    preco: float = Field(gt=0)
    foto_url: str | None = None
    disponivel: bool = True
    destaque: bool = False
    controle_estoque: bool = False
    estoque_atual: int = Field(default=0, ge=0)
    estoque_minimo: int = Field(default=0, ge=0)
    ordem: int = 0


class ProdutoUpdate(BaseModel):
    categoria_id: int | None = None
    nome: str | None = Field(default=None, min_length=2)
    descricao: str | None = None
    preco: float | None = Field(default=None, gt=0)
    foto_url: str | None = None
    disponivel: bool | None = None
    destaque: bool | None = None
    controle_estoque: bool | None = None
    estoque_atual: int | None = Field(default=None, ge=0)
    estoque_minimo: int | None = Field(default=None, ge=0)
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
    controle_estoque: bool
    estoque_atual: int
    estoque_minimo: int
    ordem: int
    grupos_modificadores: list[GrupoModificadorResponse] = []

    model_config = {"from_attributes": True}


class EstoqueAjusteRequest(BaseModel):
    operacao: str = Field(pattern="^(definir|incrementar|decrementar|zerar)$")
    valor: int = Field(default=0, ge=0)


# ── Schemas do cardápio público — sem campos de estoque ──────────────────────
# O cliente nunca sabe quanto restou. A flag `disponivel` já vem calculada
# (produto_disponivel_efetivo / modificador_disponivel_efetivo) pelo service.

class ModificadorPublicoResponse(BaseModel):
    id: int
    nome: str
    preco_adicional: float
    disponivel: bool
    ordem: int

    model_config = {"from_attributes": True}


class GrupoModificadorPublicoResponse(BaseModel):
    id: int
    nome: str
    obrigatorio: bool
    selecao_minima: int
    selecao_maxima: int
    modificadores: list[ModificadorPublicoResponse] = []

    model_config = {"from_attributes": True}


class ProdutoPublicoResponse(BaseModel):
    id: int
    categoria_id: int
    nome: str
    descricao: str | None
    preco: float
    foto_url: str | None
    disponivel: bool
    destaque: bool
    ordem: int
    grupos_modificadores: list[GrupoModificadorPublicoResponse] = []

    model_config = {"from_attributes": True}


# ── Cardápio público ──────────────────────────────────────────────────────────

class CardapioCategoriaResponse(BaseModel):
    id: int
    nome: str
    descricao: str | None
    ordem: int
    produtos: list[ProdutoPublicoResponse] = []

    model_config = {"from_attributes": True}


class CardapioPublicoResponse(BaseModel):
    categorias: list[CardapioCategoriaResponse]
    destaques: list[ProdutoPublicoResponse]
