from __future__ import annotations
import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.categoria import Categoria
from app.models.produto import Produto
from app.models.modificador import GrupoModificador, Modificador, produto_grupo_modificador


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
    """Verifica criação de grupo autônomo com opções aninhadas."""
    db = setup_db()

    grupo = GrupoModificador(
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


def test_vincular_grupo_a_produto():
    """Vínculo M:N entre grupo e produto funciona corretamente."""
    db = setup_db()
    prod = criar_produto(db)

    grupo = GrupoModificador(nome="Adicionais")
    db.add(grupo)
    db.flush()

    db.execute(produto_grupo_modificador.insert().values(
        produto_id=prod.id, grupo_id=grupo.id, ordem=1
    ))
    db.commit()

    db.refresh(prod)
    assert len(prod.grupos_modificadores) == 1
    assert prod.grupos_modificadores[0].id == grupo.id


def test_vincular_grupo_a_multiplos_produtos():
    """Mesmo grupo vinculado a dois produtos."""
    db = setup_db()
    prod1 = criar_produto(db)

    cat = db.query(Categoria).first()
    prod2 = Produto(categoria_id=cat.id, nome="Segundo", preco=20.0)
    db.add(prod2)
    db.flush()

    grupo = GrupoModificador(nome="Molho extra")
    db.add(grupo)
    db.flush()

    db.execute(produto_grupo_modificador.insert().values(
        produto_id=prod1.id, grupo_id=grupo.id, ordem=1
    ))
    db.execute(produto_grupo_modificador.insert().values(
        produto_id=prod2.id, grupo_id=grupo.id, ordem=1
    ))
    db.commit()

    db.refresh(prod1)
    db.refresh(prod2)

    assert len(prod1.grupos_modificadores) == 1
    assert len(prod2.grupos_modificadores) == 1
    assert prod1.grupos_modificadores[0].id == grupo.id
    assert prod2.grupos_modificadores[0].id == grupo.id


def test_unique_constraint_produto_grupo():
    """Não deve permitir vincular o mesmo grupo ao mesmo produto duas vezes."""
    db = setup_db()
    prod = criar_produto(db)
    grupo = GrupoModificador(nome="Extras")
    db.add(grupo)
    db.flush()

    db.execute(produto_grupo_modificador.insert().values(
        produto_id=prod.id, grupo_id=grupo.id, ordem=1
    ))
    db.commit()

    with pytest.raises(IntegrityError):
        db.execute(produto_grupo_modificador.insert().values(
            produto_id=prod.id, grupo_id=grupo.id, ordem=2
        ))
        db.commit()


def test_deletar_produto_remove_vinculo():
    """Deletar produto deve remover os vínculos mas manter o grupo."""
    db = setup_db()
    prod = criar_produto(db)
    grupo = GrupoModificador(nome="Adicionais")
    db.add(grupo)
    db.flush()

    db.execute(produto_grupo_modificador.insert().values(
        produto_id=prod.id, grupo_id=grupo.id, ordem=1
    ))
    db.commit()

    prod_id = prod.id
    grupo_id = grupo.id

    db.delete(prod)
    db.commit()

    assert db.get(GrupoModificador, grupo_id) is not None
    vinculos = db.execute(
        select(produto_grupo_modificador).where(
            produto_grupo_modificador.c.produto_id == prod_id
        )
    ).all()
    assert len(vinculos) == 0


def test_deletar_grupo_deleta_modificadores_e_vinculos():
    """Cascade: deletar grupo deve deletar opções e vínculos."""
    db = setup_db()
    prod = criar_produto(db)

    grupo = GrupoModificador(nome="Adicionais")
    db.add(grupo)
    db.flush()
    db.add(Modificador(grupo_id=grupo.id, nome="Bacon extra", preco_adicional=3.0))
    db.execute(produto_grupo_modificador.insert().values(
        produto_id=prod.id, grupo_id=grupo.id, ordem=1
    ))
    db.commit()

    grupo_id = grupo.id
    db.delete(grupo)
    db.commit()

    assert db.query(Modificador).filter(Modificador.grupo_id == grupo_id).count() == 0
    vinculos = db.execute(
        select(produto_grupo_modificador).where(
            produto_grupo_modificador.c.grupo_id == grupo_id
        )
    ).all()
    assert len(vinculos) == 0


def test_modificador_sem_grupo_invalido():
    """Modificador sem grupo deve falhar."""
    db = setup_db()
    db.add(Modificador(grupo_id=999, nome="Órfão", preco_adicional=0.0))
    with pytest.raises(IntegrityError):
        db.commit()
