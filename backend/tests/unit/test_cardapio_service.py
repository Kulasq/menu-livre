from __future__ import annotations
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.database import Base
from app.models.categoria import Categoria
from app.models.produto import Produto
from app.schemas.cardapio import (
    CategoriaCreate, CategoriaUpdate,
    ProdutoCreate, ProdutoUpdate,
)
from app.services.cardapio_service import (
    listar_categorias, criar_categoria, atualizar_categoria, deletar_categoria,
    criar_produto, atualizar_produto, deletar_produto, obter_cardapio_publico,
)


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def configurar(conn, rec):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def criar_cat(db, nome="Hambúrgueres", ordem=0):
    cat = Categoria(nome=nome, ordem=ordem)
    db.add(cat)
    db.commit()
    return db.query(Categoria).filter(Categoria.nome == nome).first()


# ── Categorias ───────────────────────────────────────────────────────────────

def test_criar_e_listar_categoria():
    db = setup_db()
    criar_categoria(CategoriaCreate(nome="Hambúrgueres", ordem=1), db)
    criar_categoria(CategoriaCreate(nome="Bebidas", ordem=2), db)

    categorias = listar_categorias(db)
    assert len(categorias) == 2


def test_atualizar_categoria():
    db = setup_db()
    cat = criar_cat(db)

    atualizada = atualizar_categoria(
        cat.id, CategoriaUpdate(nome="Burgers"), db
    )
    assert atualizada.nome == "Burgers"


def test_deletar_categoria_com_produto_falha():
    db = setup_db()
    cat = criar_cat(db)
    db.add(Produto(categoria_id=cat.id, nome="X-Burguer", preco=25.0))
    db.commit()

    with pytest.raises(HTTPException) as exc:
        deletar_categoria(cat.id, db)
    assert exc.value.status_code == 400


def test_deletar_categoria_sem_produtos():
    db = setup_db()
    cat = criar_cat(db)
    deletar_categoria(cat.id, db)

    assert listar_categorias(db) == []


# ── Produtos ─────────────────────────────────────────────────────────────────

def test_criar_produto():
    db = setup_db()
    cat = criar_cat(db)

    produto = criar_produto(
        ProdutoCreate(categoria_id=cat.id, nome="Bacontentão", preco=44.90),
        db,
    )
    assert produto.id is not None
    assert produto.nome == "Bacontentão"
    assert produto.disponivel is True


def test_criar_produto_categoria_inexistente():
    db = setup_db()
    with pytest.raises(HTTPException) as exc:
        criar_produto(
            ProdutoCreate(categoria_id=999, nome="Fantasma", preco=10.0),
            db,
        )
    assert exc.value.status_code == 404


def test_cardapio_publico_so_retorna_disponiveis():
    db = setup_db()
    cat = criar_cat(db)
    db.add(Produto(categoria_id=cat.id, nome="Disponível", preco=20.0, disponivel=True))
    db.add(Produto(categoria_id=cat.id, nome="Indisponível", preco=20.0, disponivel=False))
    db.commit()

    cardapio = obter_cardapio_publico(db)
    nomes = [p.nome for cat in cardapio["categorias"] for p in cat["produtos"]]
    assert "Disponível" in nomes
    assert "Indisponível" not in nomes


def test_produto_destaque_aparece_em_destaques():
    db = setup_db()
    cat = criar_cat(db)
    db.add(Produto(categoria_id=cat.id, nome="Destaque", preco=30.0, destaque=True))
    db.add(Produto(categoria_id=cat.id, nome="Normal", preco=20.0, destaque=False))
    db.commit()

    cardapio = obter_cardapio_publico(db)
    nomes_destaque = [p.nome for p in cardapio["destaques"]]
    assert "Destaque" in nomes_destaque
    assert "Normal" not in nomes_destaque