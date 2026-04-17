from __future__ import annotations
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.cliente import Cliente, Endereco
from app.services import cliente_service


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def configurar(conn, rec):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _criar_cliente(db, telefone="81999990099") -> Cliente:
    c = Cliente(nome="Teste", telefone=telefone)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ── listar_enderecos ──────────────────────────────────────────────────────────

def test_listar_enderecos_vazio():
    db = setup_db()
    c = _criar_cliente(db)
    result = cliente_service.listar_enderecos(db, c.id)
    assert result == []


def test_listar_enderecos_ordem_desc():
    """Endereços retornam do mais recente para o mais antigo."""
    db = setup_db()
    c = _criar_cliente(db)
    from datetime import datetime, timezone, timedelta

    e1 = Endereco(
        cliente_id=c.id,
        endereco="Rua A, 1",
        criado_em=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    e2 = Endereco(
        cliente_id=c.id,
        endereco="Rua B, 2",
        criado_em=datetime.now(timezone.utc),
    )
    db.add_all([e1, e2])
    db.commit()

    result = cliente_service.listar_enderecos(db, c.id)
    assert result[0].endereco == "Rua B, 2"
    assert result[1].endereco == "Rua A, 1"


# ── salvar_endereco_se_novo ───────────────────────────────────────────────────

def test_salvar_endereco_novo():
    db = setup_db()
    c = _criar_cliente(db)
    cliente_service.salvar_endereco_se_novo(db, c.id, "Rua Nova, 10")
    result = cliente_service.listar_enderecos(db, c.id)
    assert len(result) == 1
    assert result[0].endereco == "Rua Nova, 10"


def test_salvar_endereco_deduplicacao():
    """Mesmo endereço (case/espaço insensível) não é salvo duas vezes."""
    db = setup_db()
    c = _criar_cliente(db)
    cliente_service.salvar_endereco_se_novo(db, c.id, "Rua Nova, 10")
    cliente_service.salvar_endereco_se_novo(db, c.id, "  rua nova, 10  ")
    result = cliente_service.listar_enderecos(db, c.id)
    assert len(result) == 1


def test_salvar_endereco_limite_5():
    """Ao salvar o 6º endereço, o mais antigo é removido."""
    db = setup_db()
    c = _criar_cliente(db)
    from datetime import datetime, timezone, timedelta

    for i in range(5):
        e = Endereco(
            cliente_id=c.id,
            endereco=f"Rua {i}, {i}",
            criado_em=datetime.now(timezone.utc) - timedelta(minutes=10 - i),
        )
        db.add(e)
    db.commit()

    cliente_service.salvar_endereco_se_novo(db, c.id, "Rua Nova, 99")
    result = cliente_service.listar_enderecos(db, c.id)
    assert len(result) == 5
    enderecos_texto = [e.endereco for e in result]
    assert "Rua 0, 0" not in enderecos_texto  # mais antigo foi removido
    assert "Rua Nova, 99" in enderecos_texto


def test_salvar_endereco_vazio_ignorado():
    """Endereço vazio ou só espaços não deve ser salvo."""
    db = setup_db()
    c = _criar_cliente(db)
    cliente_service.salvar_endereco_se_novo(db, c.id, "   ")
    result = cliente_service.listar_enderecos(db, c.id)
    assert result == []


# ── deletar_endereco ──────────────────────────────────────────────────────────

def test_deletar_endereco_proprio():
    db = setup_db()
    c = _criar_cliente(db)
    e = Endereco(cliente_id=c.id, endereco="Rua X, 5")
    db.add(e)
    db.commit()
    db.refresh(e)

    cliente_service.deletar_endereco(db, e.id, c.id)
    assert cliente_service.listar_enderecos(db, c.id) == []


def test_deletar_endereco_de_outro_cliente_falha():
    """Não permite deletar endereço que não pertence ao cliente autenticado."""
    from fastapi import HTTPException
    db = setup_db()
    c1 = _criar_cliente(db, "81999990011")
    c2 = _criar_cliente(db, "81999990022")

    e = Endereco(cliente_id=c1.id, endereco="Rua Y, 7")
    db.add(e)
    db.commit()
    db.refresh(e)

    with pytest.raises(HTTPException) as exc:
        cliente_service.deletar_endereco(db, e.id, c2.id)
    assert exc.value.status_code == 403


def test_deletar_endereco_inexistente_falha():
    from fastapi import HTTPException
    db = setup_db()
    c = _criar_cliente(db)
    with pytest.raises(HTTPException) as exc:
        cliente_service.deletar_endereco(db, 9999, c.id)
    assert exc.value.status_code == 404
