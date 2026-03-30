from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.models.usuario import Usuario
from app.models.cliente import Cliente
from app.models.categoria import Categoria
from app.models.produto import Produto
from app.models.modificador import GrupoModificador, Modificador
from app.models.configuracao import Configuracao

from app.main import app as fastapi_app
from app.database import Base, get_db
from app.services.auth_service import hash_senha

import tempfile
import os

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
TEST_DB_PATH = _tmp.name
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)

@event.listens_for(_engine, "connect")
def configurar(conn, rec):
    conn.execute("PRAGMA foreign_keys=ON")

Base.metadata.create_all(_engine)
_TestSession = sessionmaker(bind=_engine)


@pytest.fixture(scope="function")
def db_teste():
    """Sessão isolada por teste — rollback ao final."""
    connection = _engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection)

    yield db

    db.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_teste):
    """Cliente HTTP com banco de teste injetado."""
    def override_get_db():
        yield db_teste

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def usuario_admin(db_teste):
    """Cria um usuário admin no banco de teste."""
    usuario = Usuario(
        nome="Sara",
        email="sara@paodeamao.com",
        senha_hash=hash_senha("senha123"),
        role="superadmin",
    )
    db_teste.add(usuario)
    db_teste.commit()
    return usuario