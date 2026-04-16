from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.services import usuario_service
from app.services.auth_service import hash_senha
from app.models.usuario import Usuario


# ── Helpers ──────────────────────────────────────────────────────────────────

def _mock_usuario(nome="Admin", email="admin@exemplo.com", senha="senha123"):
    u = MagicMock(spec=Usuario)
    u.id = 1
    u.nome = nome
    u.email = email
    u.role = "superadmin"
    u.ativo = True
    u.senha_hash = hash_senha(senha)
    return u


# ── obter_me ─────────────────────────────────────────────────────────────────

def test_obter_me_retorna_usuario():
    usuario = _mock_usuario()
    resultado = usuario_service.obter_me(usuario)
    assert resultado is usuario


# ── atualizar_me ──────────────────────────────────────────────────────────────

def test_atualizar_me_nome_e_email():
    usuario = _mock_usuario()
    db = MagicMock()
    db.query().filter().first.return_value = None  # sem conflito de e-mail

    resultado = usuario_service.atualizar_me(usuario, "Novo Nome", "novo@email.com", db)

    assert usuario.nome == "Novo Nome"
    assert usuario.email == "novo@email.com"
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(usuario)


def test_atualizar_me_normaliza_email_lowercase():
    usuario = _mock_usuario()
    db = MagicMock()
    db.query().filter().first.return_value = None

    usuario_service.atualizar_me(usuario, "Admin", "ADMIN@EXEMPLO.COM", db)

    assert usuario.email == "admin@exemplo.com"


def test_atualizar_me_email_duplicado_levanta_409():
    usuario = _mock_usuario()
    outro_usuario = _mock_usuario(email="outro@email.com")
    outro_usuario.id = 2

    db = MagicMock()
    db.query().filter().first.return_value = outro_usuario  # conflito encontrado

    with pytest.raises(HTTPException) as exc:
        usuario_service.atualizar_me(usuario, "Admin", "outro@email.com", db)

    assert exc.value.status_code == 409
    assert "e-mail" in exc.value.detail.lower()


def test_atualizar_me_mesmo_email_do_proprio_usuario_nao_conflita():
    """Salvar o mesmo e-mail do próprio usuário não deve levantar 409."""
    usuario = _mock_usuario(email="admin@exemplo.com")
    db = MagicMock()
    # Retorna None porque o filtro exclui o próprio ID (Usuario.id != usuario.id)
    db.query().filter().first.return_value = None

    # Não deve levantar exceção
    usuario_service.atualizar_me(usuario, "Admin", "admin@exemplo.com", db)
    db.commit.assert_called_once()


def test_atualizar_me_strip_nome():
    usuario = _mock_usuario()
    db = MagicMock()
    db.query().filter().first.return_value = None

    usuario_service.atualizar_me(usuario, "  Admin  ", "admin@exemplo.com", db)

    assert usuario.nome == "Admin"


# ── alterar_senha ─────────────────────────────────────────────────────────────

def test_alterar_senha_com_senha_atual_correta():
    usuario = _mock_usuario(senha="senha123")
    db = MagicMock()

    usuario_service.alterar_senha(usuario, "senha123", "novaSenha456", db)

    db.commit.assert_called_once()
    # O hash deve ter mudado
    from app.services.auth_service import verificar_senha
    assert verificar_senha("novaSenha456", usuario.senha_hash)


def test_alterar_senha_com_senha_atual_errada_levanta_400():
    usuario = _mock_usuario(senha="senha123")
    db = MagicMock()

    with pytest.raises(HTTPException) as exc:
        usuario_service.alterar_senha(usuario, "senhaErrada", "novaSenha456", db)

    assert exc.value.status_code == 400
    assert "incorreta" in exc.value.detail.lower()
    db.commit.assert_not_called()


def test_alterar_senha_nova_igual_atual_levanta_400():
    usuario = _mock_usuario(senha="senha123")
    db = MagicMock()

    with pytest.raises(HTTPException) as exc:
        usuario_service.alterar_senha(usuario, "senha123", "senha123", db)

    assert exc.value.status_code == 400
    assert "diferente" in exc.value.detail.lower()
    db.commit.assert_not_called()


def test_alterar_senha_nao_chama_commit_em_caso_de_erro():
    usuario = _mock_usuario(senha="senha123")
    db = MagicMock()

    with pytest.raises(HTTPException):
        usuario_service.alterar_senha(usuario, "errada", "novaSenha456", db)

    db.commit.assert_not_called()
