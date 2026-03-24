from __future__ import annotations
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.cliente import Cliente


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def configurar(conn, rec):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_criar_cliente():
    """Verifica que um cliente é salvo com os campos corretos."""
    db = setup_db()

    cliente = Cliente(nome="Lucas Silva", telefone="81999990001")
    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    assert cliente.id is not None
    assert cliente.nome == "Lucas Silva"
    assert cliente.telefone == "81999990001"
    assert cliente.segmento == "novo"         # default
    assert cliente.total_pedidos == 0         # default
    assert cliente.nivel_fidelidade == "bronze"  # default
    assert cliente.ativo is True              # default


def test_telefone_unico():
    """Dois clientes não podem ter o mesmo telefone."""
    db = setup_db()

    db.add(Cliente(nome="A", telefone="81999990002"))
    db.commit()

    db.add(Cliente(nome="B", telefone="81999990002"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_cliente_sem_senha():
    """Cliente não tem campo de senha — identificação só por telefone."""
    campos = [c.key for c in Cliente.__table__.columns]
    assert "senha" not in campos
    assert "senha_hash" not in campos