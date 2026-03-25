from __future__ import annotations
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from jose import jwt
from fastapi import HTTPException

from app.services.auth_service import (
    hash_senha,
    verificar_senha,
    criar_access_token,
    criar_refresh_token,
    criar_token_cliente,
    login_admin,
    renovar_access_token,
    logout_admin,
)
from app.config import settings


# ── Hash e verificação de senha ──────────────────────────────────────────────

def test_hash_senha_gera_hash_diferente_do_original():
    senha = "minha_senha_secreta"
    hashed = hash_senha(senha)
    assert hashed != senha
    assert len(hashed) > 20


def test_verificar_senha_correta():
    senha = "minha_senha_secreta"
    hashed = hash_senha(senha)
    assert verificar_senha(senha, hashed) is True


def test_verificar_senha_errada():
    hashed = hash_senha("senha_correta")
    assert verificar_senha("senha_errada", hashed) is False


# ── Tokens JWT ───────────────────────────────────────────────────────────────

def test_access_token_contem_campos_corretos():
    token = criar_access_token(user_id=42)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert payload["sub"] == "42"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_refresh_token_contem_campos_corretos():
    token = criar_refresh_token(user_id=42)
    payload = jwt.decode(token, settings.REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert payload["sub"] == "42"
    assert payload["type"] == "refresh"


def test_token_cliente_contem_type_cliente():
    token = criar_token_cliente(cliente_id=10)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert payload["sub"] == "10"
    assert payload["type"] == "cliente"


# ── Login ────────────────────────────────────────────────────────────────────

def _mock_usuario(ativo=True):
    """Cria um mock de usuário para os testes de login."""
    from app.services.auth_service import hash_senha
    usuario = MagicMock()
    usuario.id = 1
    usuario.nome = "Dona Cris"
    usuario.role = "superadmin"
    usuario.ativo = ativo
    usuario.senha_hash = hash_senha("senha123")
    return usuario


def test_login_retorna_tokens_com_credenciais_corretas():
    db = MagicMock()
    db.query().filter().first.return_value = _mock_usuario()

    resultado = login_admin("cris@paodeamao.com", "senha123", db)

    assert "access_token" in resultado
    assert "refresh_token" in resultado
    assert resultado["token_type"] == "bearer"
    assert resultado["usuario_nome"] == "Dona Cris"


def test_login_falha_com_senha_errada():
    db = MagicMock()
    db.query().filter().first.return_value = _mock_usuario()

    with pytest.raises(HTTPException) as exc:
        login_admin("cris@paodeamao.com", "senha_errada", db)

    assert exc.value.status_code == 401


def test_login_falha_com_usuario_inexistente():
    db = MagicMock()
    db.query().filter().first.return_value = None

    with pytest.raises(HTTPException) as exc:
        login_admin("naoexiste@email.com", "qualquer", db)

    assert exc.value.status_code == 401


def test_login_falha_com_usuario_inativo():
    db = MagicMock()
    db.query().filter().first.return_value = _mock_usuario(ativo=False)

    with pytest.raises(HTTPException) as exc:
        login_admin("cris@paodeamao.com", "senha123", db)

    assert exc.value.status_code == 403


# ── Logout e invalidação de token ────────────────────────────────────────────

def test_logout_invalida_refresh_token():
    token = criar_refresh_token(user_id=1)
    logout_admin(token)

    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        renovar_access_token(token, db)

    assert exc.value.status_code == 401