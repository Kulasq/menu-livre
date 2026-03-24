from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
import pytest
from sqlalchemy.exc import IntegrityError

from app.database import Base
from app.models.categoria import Categoria
from app.models.produto import Produto


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def configurar(conn, rec):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def criar_categoria(db, nome="Hambúrgueres"):
    cat = Categoria(nome=nome)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def test_criar_produto():
    """Verifica que um produto é salvo com todos os campos."""
    db = setup_db()
    cat = criar_categoria(db)

    produto = Produto(
        categoria_id=cat.id,
        nome="Bacontentão",
        descricao="Hambúrguer com bacon",
        preco=44.90,
    )
    db.add(produto)
    db.commit()
    db.refresh(produto)

    assert produto.id is not None
    assert produto.nome == "Bacontentão"
    assert produto.preco == 44.90
    assert produto.disponivel is True   # default
    assert produto.destaque is False    # default
    assert produto.estoque_atual == 0   # default


def test_produto_sem_categoria_invalido():
    """Produto com categoria inexistente deve falhar (foreign key)."""
    db = setup_db()

    db.add(Produto(categoria_id=999, nome="Fantasma", preco=10.0))
    with pytest.raises(IntegrityError):
        db.commit()


def test_relacionamento_categoria():
    """Verifica que produto.categoria retorna a categoria correta."""
    db = setup_db()
    cat = criar_categoria(db, nome="Combos")

    produto = Produto(categoria_id=cat.id, nome="Combo Clássico", preco=35.0)
    db.add(produto)
    db.commit()
    db.refresh(produto)

    assert produto.categoria.nome == "Combos"