from __future__ import annotations
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.categoria import Categoria
from app.models.produto import Produto
from app.models.modificador import GrupoModificador, Modificador


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def configurar(conn, rec):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def criar_produto(db):
    cat = Categoria(nome="Hambúrgueres")
    db.add(cat)
    db.flush()
    prod = Produto(categoria_id=cat.id, nome="Bacontentão", preco=44.90)
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return prod


def test_criar_grupo_com_modificadores():
    """Verifica criação de grupo com opções aninhadas."""
    db = setup_db()
    prod = criar_produto(db)

    grupo = GrupoModificador(
        produto_id=prod.id,
        nome="Ponto da carne",
        obrigatorio=True,
        selecao_minima=1,
        selecao_maxima=1,
    )
    db.add(grupo)
    db.flush()

    for nome in ["Mal passado", "Ao ponto", "Bem passado"]:
        db.add(Modificador(grupo_id=grupo.id, nome=nome))

    db.commit()
    db.refresh(grupo)

    assert len(grupo.modificadores) == 3
    assert grupo.obrigatorio is True


def test_deletar_grupo_deleta_modificadores():
    """Cascade: deletar grupo deve deletar todas as opções."""
    db = setup_db()
    prod = criar_produto(db)

    grupo = GrupoModificador(produto_id=prod.id, nome="Adicionais")
    db.add(grupo)
    db.flush()
    db.add(Modificador(grupo_id=grupo.id, nome="Bacon extra", preco_adicional=3.0))
    db.commit()

    grupo_id = grupo.id
    db.delete(grupo)
    db.commit()

    restantes = db.query(Modificador).filter(Modificador.grupo_id == grupo_id).all()
    assert len(restantes) == 0


def test_modificador_sem_grupo_invalido():
    """Modificador sem grupo deve falhar."""
    db = setup_db()
    db.add(Modificador(grupo_id=999, nome="Órfão", preco_adicional=0.0))
    with pytest.raises(IntegrityError):
        db.commit()