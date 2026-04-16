from __future__ import annotations
import pytest

# ── Helpers ──────────────────────────────────────────────────────────────────

def _login(client, email="admin@exemplo.com", senha="senha123"):
    r = client.post("/api/auth/login", json={"email": email, "senha": senha})
    assert r.status_code == 200
    return r.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


# ── GET /api/auth/me ──────────────────────────────────────────────────────────

def test_get_me_sem_token_retorna_401(client, usuario_admin):
    r = client.get("/api/auth/me")
    assert r.status_code == 403  # HTTPBearer retorna 403 sem credencial


def test_get_me_retorna_dados_do_usuario(client, usuario_admin):
    token = _login(client)
    r = client.get("/api/auth/me", headers=_headers(token))

    assert r.status_code == 200
    data = r.json()
    assert data["nome"] == "Admin"
    assert data["email"] == "admin@exemplo.com"
    assert data["role"] == "superadmin"
    assert "id" in data
    # Nunca expor senha
    assert "senha" not in data
    assert "senha_hash" not in data


# ── PUT /api/auth/me ──────────────────────────────────────────────────────────

def test_put_me_atualiza_nome(client, usuario_admin):
    token = _login(client)
    r = client.put(
        "/api/auth/me",
        headers=_headers(token),
        json={"nome": "Lucas Admin", "email": "admin@exemplo.com"},
    )

    assert r.status_code == 200
    assert r.json()["nome"] == "Lucas Admin"


def test_put_me_atualiza_email(client, usuario_admin):
    token = _login(client)
    r = client.put(
        "/api/auth/me",
        headers=_headers(token),
        json={"nome": "Admin", "email": "novo@email.com"},
    )

    assert r.status_code == 200
    assert r.json()["email"] == "novo@email.com"


def test_put_me_email_invalido_retorna_422(client, usuario_admin):
    token = _login(client)
    r = client.put(
        "/api/auth/me",
        headers=_headers(token),
        json={"nome": "Admin", "email": "nao-e-um-email"},
    )
    assert r.status_code == 422


def test_put_me_nome_vazio_retorna_422(client, usuario_admin):
    token = _login(client)
    r = client.put(
        "/api/auth/me",
        headers=_headers(token),
        json={"nome": "   ", "email": "admin@exemplo.com"},
    )
    assert r.status_code == 422


def test_put_me_sem_token_retorna_403(client, usuario_admin):
    r = client.put(
        "/api/auth/me",
        json={"nome": "Admin", "email": "admin@exemplo.com"},
    )
    assert r.status_code == 403


def test_put_me_email_duplicado_retorna_409(client, usuario_admin, db_teste):
    """Criar segundo usuário e tentar usar o e-mail do primeiro."""
    from app.models.usuario import Usuario
    from app.services.auth_service import hash_senha

    segundo = Usuario(
        nome="Segundo",
        email="segundo@exemplo.com",
        senha_hash=hash_senha("senha456"),
        role="admin",
    )
    db_teste.add(segundo)
    db_teste.commit()

    # Login como segundo e tenta usar e-mail do admin
    token = _login(client, "segundo@exemplo.com", "senha456")
    r = client.put(
        "/api/auth/me",
        headers=_headers(token),
        json={"nome": "Segundo", "email": "admin@exemplo.com"},
    )
    assert r.status_code == 409


# ── PUT /api/auth/alterar-senha ───────────────────────────────────────────────

def test_alterar_senha_com_sucesso(client, usuario_admin):
    token = _login(client)
    r = client.put(
        "/api/auth/alterar-senha",
        headers=_headers(token),
        json={
            "senha_atual": "senha123",
            "senha_nova": "novaSenha456",
            "confirmar_senha": "novaSenha456",
        },
    )
    assert r.status_code == 204

    # Deve conseguir logar com a nova senha
    novo_login = client.post("/api/auth/login", json={
        "email": "admin@exemplo.com",
        "senha": "novaSenha456",
    })
    assert novo_login.status_code == 200


def test_alterar_senha_atual_errada_retorna_400(client, usuario_admin):
    token = _login(client)
    r = client.put(
        "/api/auth/alterar-senha",
        headers=_headers(token),
        json={
            "senha_atual": "senhaErrada",
            "senha_nova": "novaSenha456",
            "confirmar_senha": "novaSenha456",
        },
    )
    assert r.status_code == 400
    assert "incorreta" in r.json()["detail"].lower()


def test_alterar_senha_nova_igual_atual_retorna_400(client, usuario_admin):
    token = _login(client)
    r = client.put(
        "/api/auth/alterar-senha",
        headers=_headers(token),
        json={
            "senha_atual": "senha123",
            "senha_nova": "senha123",
            "confirmar_senha": "senha123",
        },
    )
    assert r.status_code == 400


def test_alterar_senha_confirmar_divergente_retorna_422(client, usuario_admin):
    token = _login(client)
    r = client.put(
        "/api/auth/alterar-senha",
        headers=_headers(token),
        json={
            "senha_atual": "senha123",
            "senha_nova": "novaSenha456",
            "confirmar_senha": "senhaErrada",
        },
    )
    assert r.status_code == 422


def test_alterar_senha_nova_muito_curta_retorna_422(client, usuario_admin):
    token = _login(client)
    r = client.put(
        "/api/auth/alterar-senha",
        headers=_headers(token),
        json={
            "senha_atual": "senha123",
            "senha_nova": "abc",
            "confirmar_senha": "abc",
        },
    )
    assert r.status_code == 422


def test_alterar_senha_sem_token_retorna_403(client, usuario_admin):
    r = client.put(
        "/api/auth/alterar-senha",
        json={
            "senha_atual": "senha123",
            "senha_nova": "novaSenha456",
            "confirmar_senha": "novaSenha456",
        },
    )
    assert r.status_code == 403
