from __future__ import annotations
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from app.models.categoria import Categoria
from app.models.produto import Produto
from app.models.modificador import GrupoModificador, Modificador
from app.schemas.cardapio import (
    CategoriaCreate, CategoriaUpdate,
    ProdutoCreate, ProdutoUpdate,
    GrupoModificadorCreate,
    ModificadorCreate,
)


# ── Categorias ───────────────────────────────────────────────────────────────

def listar_categorias(db: Session, apenas_ativas: bool = False) -> list[Categoria]:
    q = db.query(Categoria)
    if apenas_ativas:
        q = q.filter(Categoria.ativo == True)
    return q.order_by(Categoria.ordem, Categoria.nome).all()


def criar_categoria(dados: CategoriaCreate, db: Session) -> Categoria:
    categoria = Categoria(**dados.model_dump())
    db.add(categoria)
    db.commit()
    categoria_id = categoria.id
    categoria_nome = categoria.nome
    db.expire(categoria)
    return db.get(Categoria, categoria_id)


def atualizar_categoria(categoria_id: int, dados: CategoriaUpdate, db: Session) -> Categoria:
    categoria = db.get(Categoria, categoria_id)
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(categoria, campo, valor)
    db.commit()
    return db.get(Categoria, categoria_id)


def deletar_categoria(categoria_id: int, db: Session) -> None:
    categoria = db.get(Categoria, categoria_id)
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    count = db.query(Produto).filter(Produto.categoria_id == categoria_id).count()
    if count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível excluir: categoria tem {count} produto(s)",
        )
    db.delete(categoria)
    db.commit()


# ── Produtos ─────────────────────────────────────────────────────────────────

def listar_produtos(db: Session, apenas_disponiveis: bool = False) -> list[Produto]:
    q = db.query(Produto).options(
        joinedload(Produto.grupos_modificadores).joinedload(GrupoModificador.modificadores)
    )
    if apenas_disponiveis:
        q = q.filter(Produto.disponivel == True)
    return q.order_by(Produto.ordem, Produto.nome).all()


def obter_produto(produto_id: int, db: Session) -> Produto:
    produto = db.query(Produto).options(
        joinedload(Produto.grupos_modificadores).joinedload(GrupoModificador.modificadores)
    ).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return produto


def criar_produto(dados: ProdutoCreate, db: Session) -> Produto:
    categoria = db.get(Categoria, dados.categoria_id)
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    produto = Produto(**dados.model_dump())
    db.add(produto)
    db.commit()
    produto_id = produto.id
    return obter_produto(produto_id, db)


def atualizar_produto(produto_id: int, dados: ProdutoUpdate, db: Session) -> Produto:
    produto = db.get(Produto, produto_id)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if dados.categoria_id:
        if not db.get(Categoria, dados.categoria_id):
            raise HTTPException(status_code=404, detail="Categoria não encontrada")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(produto, campo, valor)
    db.commit()
    return obter_produto(produto_id, db)


def deletar_produto(produto_id: int, db: Session) -> None:
    produto = db.get(Produto, produto_id)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    db.delete(produto)
    db.commit()


# ── Cardápio público ──────────────────────────────────────────────────────────

def obter_cardapio_publico(db: Session) -> dict:
    categorias = listar_categorias(db, apenas_ativas=True)
    produtos = listar_produtos(db, apenas_disponiveis=True)

    produtos_por_categoria: dict[int, list] = {}
    destaques = []

    for produto in produtos:
        produtos_por_categoria.setdefault(produto.categoria_id, []).append(produto)
        if produto.destaque:
            destaques.append(produto)

    resultado = []
    for cat in categorias:
        resultado.append({
            "id": cat.id,
            "nome": cat.nome,
            "descricao": cat.descricao,
            "ordem": cat.ordem,
            "produtos": produtos_por_categoria.get(cat.id, []),
        })

    return {"categorias": resultado, "destaques": destaques}