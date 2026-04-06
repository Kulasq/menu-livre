from __future__ import annotations
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.schemas.cardapio import (
    CategoriaCreate, CategoriaUpdate, CategoriaResponse,
    ProdutoCreate, ProdutoUpdate, ProdutoResponse,
    GrupoModificadorCreate, GrupoModificadorUpdate, GrupoModificadorResponse,
    ModificadorCreate, ModificadorUpdate, ModificadorResponse,
)
from app.services import cardapio_service

router = APIRouter(prefix="/api/admin", tags=["admin-cardapio"])


# ── Categorias ───────────────────────────────────────────────────────────────

@router.get("/categorias", response_model=list[CategoriaResponse])
def listar_categorias(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.listar_categorias(db)


@router.post("/categorias", response_model=CategoriaResponse, status_code=201)
def criar_categoria(
    dados: CategoriaCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.criar_categoria(dados, db)


@router.put("/categorias/{categoria_id}", response_model=CategoriaResponse)
def atualizar_categoria(
    categoria_id: int,
    dados: CategoriaUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.atualizar_categoria(categoria_id, dados, db)


@router.delete("/categorias/{categoria_id}", status_code=204)
def deletar_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    cardapio_service.deletar_categoria(categoria_id, db)


# ── Produtos ─────────────────────────────────────────────────────────────────

@router.get("/produtos", response_model=list[ProdutoResponse])
def listar_produtos(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.listar_produtos(db)


@router.post("/produtos", response_model=ProdutoResponse, status_code=201)
def criar_produto(
    dados: ProdutoCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.criar_produto(dados, db)


@router.put("/produtos/{produto_id}", response_model=ProdutoResponse)
def atualizar_produto(
    produto_id: int,
    dados: ProdutoUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.atualizar_produto(produto_id, dados, db)


@router.delete("/produtos/{produto_id}", status_code=204)
def deletar_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    cardapio_service.deletar_produto(produto_id, db)

# ── Grupos de Modificadores ──────────────────────────────────────────────────
 
@router.post(
    "/produtos/{produto_id}/modificadores",
    response_model=GrupoModificadorResponse,
    status_code=201,
)
def criar_grupo_modificador(
    produto_id: int,
    dados: GrupoModificadorCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.criar_grupo_modificador(produto_id, dados, db)
 
 
@router.put(
    "/modificadores/{grupo_id}",
    response_model=GrupoModificadorResponse,
)
def atualizar_grupo_modificador(
    grupo_id: int,
    dados: GrupoModificadorUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.atualizar_grupo_modificador(grupo_id, dados, db)
 
 
@router.delete("/modificadores/{grupo_id}", status_code=204)
def deletar_grupo_modificador(
    grupo_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    cardapio_service.deletar_grupo_modificador(grupo_id, db)
 
 
# ── Modificadores (opções individuais) ───────────────────────────────────────
 
@router.post(
    "/modificadores/{grupo_id}/opcoes",
    response_model=ModificadorResponse,
    status_code=201,
)
def criar_modificador(
    grupo_id: int,
    dados: ModificadorCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.criar_modificador(grupo_id, dados, db)
 
 
@router.put(
    "/modificadores/opcoes/{modificador_id}",
    response_model=ModificadorResponse,
)
def atualizar_modificador(
    modificador_id: int,
    dados: ModificadorUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cardapio_service.atualizar_modificador(modificador_id, dados, db)
 
 
@router.delete("/modificadores/opcoes/{modificador_id}", status_code=204)
def deletar_modificador(
    modificador_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    cardapio_service.deletar_modificador(modificador_id, db)