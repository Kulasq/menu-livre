from __future__ import annotations
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from app.models.categoria import Categoria
from app.models.produto import Produto
from app.models.modificador import GrupoModificador, Modificador
from app.schemas.cardapio import (
    CategoriaCreate, CategoriaUpdate,
    ProdutoCreate, ProdutoUpdate,
    GrupoModificadorCreate, GrupoModificadorUpdate,
    ModificadorCreate, ModificadorUpdate,
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

def criar_grupo_modificador(produto_id: int, dados: GrupoModificadorCreate, db: Session) -> GrupoModificador:
    produto = db.get(Produto, produto_id)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
 
    grupo = GrupoModificador(
        produto_id=produto_id,
        nome=dados.nome,
        obrigatorio=dados.obrigatorio,
        selecao_minima=dados.selecao_minima,
        selecao_maxima=dados.selecao_maxima,
        ordem=dados.ordem,
    )
    db.add(grupo)
    db.flush()
 
    for mod_dados in dados.modificadores:
        mod = Modificador(
            grupo_id=grupo.id,
            nome=mod_dados.nome,
            preco_adicional=mod_dados.preco_adicional,
            disponivel=mod_dados.disponivel,
            ordem=mod_dados.ordem,
        )
        db.add(mod)
 
    db.commit()
    grupo_id = grupo.id
    return db.query(GrupoModificador).options(
        joinedload(GrupoModificador.modificadores)
    ).filter(GrupoModificador.id == grupo_id).first()
 
 
def atualizar_grupo_modificador(
    grupo_id: int, dados: "GrupoModificadorUpdate", db: Session
) -> GrupoModificador:
    grupo = db.get(GrupoModificador, grupo_id)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo de modificador não encontrado")
 
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(grupo, campo, valor)
 
    db.commit()
    return db.query(GrupoModificador).options(
        joinedload(GrupoModificador.modificadores)
    ).filter(GrupoModificador.id == grupo_id).first()
 
 
def deletar_grupo_modificador(grupo_id: int, db: Session) -> None:
    grupo = db.get(GrupoModificador, grupo_id)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo de modificador não encontrado")
    db.delete(grupo)
    db.commit()
 
 
# ── Modificadores (opções individuais) ────────────────────────────────────────
 
def criar_modificador(grupo_id: int, dados: ModificadorCreate, db: Session) -> Modificador:
    grupo = db.get(GrupoModificador, grupo_id)
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo de modificador não encontrado")
 
    mod = Modificador(
        grupo_id=grupo_id,
        nome=dados.nome,
        preco_adicional=dados.preco_adicional,
        disponivel=dados.disponivel,
        ordem=dados.ordem,
    )
    db.add(mod)
    db.commit()
    mod_id = mod.id
    return db.get(Modificador, mod_id)
 
 
def atualizar_modificador(
    modificador_id: int, dados: "ModificadorUpdate", db: Session
) -> Modificador:
    mod = db.get(Modificador, modificador_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Modificador não encontrado")
 
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(mod, campo, valor)
 
    db.commit()
    return db.get(Modificador, modificador_id)
 
 
def deletar_modificador(modificador_id: int, db: Session) -> None:
    mod = db.get(Modificador, modificador_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Modificador não encontrado")
    db.delete(mod)
    db.commit()