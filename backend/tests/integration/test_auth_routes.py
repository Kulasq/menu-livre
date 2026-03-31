from __future__ import annotations
import pytest


def test_login_com_credenciais_corretas(client, usuario_admin):
    response = client.post("/api/auth/login", json={
        "email": "sara@paodeamao.com",
        "senha": "senha123",
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["usuario_nome"] == "Sara"


def test_login_com_senha_errada(client, usuario_admin):
    response = client.post("/api/auth/login", json={
        "email": "sara@paodeamao.com",
        "senha": "senha_errada",
    })

    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou senha incorretos"


def test_login_com_usuario_inexistente(client, usuario_admin):
    response = client.post("/api/auth/login", json={
        "email": "naoexiste@email.com",
        "senha": "qualquer",
    })

    assert response.status_code == 401


def test_rota_protegida_sem_token(client):
    """Qualquer rota /api/admin/* deve rejeitar sem token."""
    response = client.get("/api/admin/categorias")
    assert response.status_code in (401, 403, 404)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_refresh_com_token_valido(client, usuario_admin):
    login = client.post("/api/auth/login", json={
        "email": "sara@paodeamao.com",
        "senha": "senha123",
    })
    refresh_token = login.json()["refresh_token"]

    response = client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token,
    })

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_logout_invalida_token(client, usuario_admin):
    login = client.post("/api/auth/login", json={
        "email": "sara@paodeamao.com",
        "senha": "senha123",
    })
    refresh_token = login.json()["refresh_token"]

    client.post("/api/auth/logout", json={"refresh_token": refresh_token})

    response = client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert response.status_code == 401