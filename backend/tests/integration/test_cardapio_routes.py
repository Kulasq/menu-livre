from __future__ import annotations
import pytest
from app.models.usuario import Usuario
from app.services.auth_service import hash_senha


def obter_token(client, usuario_admin) -> str:
    response = client.post("/api/auth/login", json={
        "email": "sara@paodeamao.com",
        "senha": "senha123",
    })
    return response.json()["access_token"]


# ── Categorias ───────────────────────────────────────────────────────────────

def test_criar_categoria_autenticado(client, usuario_admin):
    token = obter_token(client, usuario_admin)

    response = client.post(
        "/api/admin/categorias",
        json={"nome": "Hambúrgueres", "ordem": 1},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "Hambúrgueres"
    assert data["ativo"] is True


def test_criar_categoria_sem_token(client):
    response = client.post(
        "/api/admin/categorias",
        json={"nome": "Hambúrgueres"},
    )
    assert response.status_code == 403


def test_listar_categorias(client, usuario_admin):
    token = obter_token(client, usuario_admin)

    client.post(
        "/api/admin/categorias",
        json={"nome": "Hambúrgueres", "ordem": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/api/admin/categorias",
        json={"nome": "Bebidas", "ordem": 2},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get(
        "/api/admin/categorias",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_deletar_categoria_inexistente(client, usuario_admin):
    token = obter_token(client, usuario_admin)

    response = client.delete(
        "/api/admin/categorias/999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ── Produtos ─────────────────────────────────────────────────────────────────

def test_criar_produto(client, usuario_admin):
    token = obter_token(client, usuario_admin)

    cat = client.post(
        "/api/admin/categorias",
        json={"nome": "Hambúrgueres"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    response = client.post(
        "/api/admin/produtos",
        json={"categoria_id": cat["id"], "nome": "Bacontentão", "preco": 44.90},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "Bacontentão"
    assert data["preco"] == 44.90
    assert data["disponivel"] is True


def test_cardapio_publico_vazio(client):
    response = client.get("/api/cardapio")
    assert response.status_code == 200
    data = response.json()
    assert data["categorias"] == []
    assert data["destaques"] == []


def test_cardapio_publico_com_produto(client, usuario_admin):
    token = obter_token(client, usuario_admin)

    cat = client.post(
        "/api/admin/categorias",
        json={"nome": "Hambúrgueres"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    client.post(
        "/api/admin/produtos",
        json={"categoria_id": cat["id"], "nome": "X-Burguer", "preco": 25.0},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get("/api/cardapio")
    assert response.status_code == 200
    data = response.json()
    assert len(data["categorias"]) == 1
    assert len(data["categorias"][0]["produtos"]) == 1
    assert data["categorias"][0]["produtos"][0]["nome"] == "X-Burguer"