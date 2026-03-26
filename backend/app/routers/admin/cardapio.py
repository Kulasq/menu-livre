from __future__ import annotations
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.schemas.cardapio import (
    CategoriaCreate, CategoriaUpdate, CategoriaResponse,
    ProdutoCreate, ProdutoUpdate, ProdutoResponse,
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