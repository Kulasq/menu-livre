"""
Testes de segurança: validação de tipo de token nos pontos de entrada da API.

Cobre o comportamento de deps.get_current_admin e deps.get_current_cliente
quando recebem o tipo de token errado, tokens adulterados ou usuário inativo.
"""
from __future__ import annotations
import pytest

from app.services.auth_service import (
    criar_access_token,
    criar_refresh_token,
    criar_token_cliente,
)
from app.models.cliente import Cliente


# ── Rotas admin com tipo de token errado ──────────────────────────────────────

def test_rota_admin_com_token_tipo_cliente_rejeitado(client, usuario_admin):
    """Token de cliente (type='cliente') não deve ser aceito em rotas admin."""
    token_cliente = criar_token_cliente(cliente_id=999)

    response = client.get(
        "/api/admin/categorias",
        headers={"Authorization": f"Bearer {token_cliente}"},
    )
    assert response.status_code == 401


def test_rota_admin_com_token_tipo_refresh_rejeitado(client, usuario_admin):
    """Refresh token (type='refresh') não deve ser aceito em rotas admin."""
    token_refresh = criar_refresh_token(user_id=usuario_admin.id)

    response = client.get(
        "/api/admin/categorias",
        headers={"Authorization": f"Bearer {token_refresh}"},
    )
    assert response.status_code == 401


def test_rota_admin_com_jwt_adulterado_rejeitado(client, usuario_admin):
    """JWT com assinatura corrompida deve ser rejeitado."""
    token_valido = criar_access_token(user_id=usuario_admin.id)
    token_adulterado = token_valido[:-8] + "XXXXXXXX"

    response = client.get(
        "/api/admin/categorias",
        headers={"Authorization": f"Bearer {token_adulterado}"},
    )
    assert response.status_code == 401


def test_rota_admin_com_usuario_inativo_rejeitado(client, usuario_admin, db_teste):
    """Access token válido de usuário desativado deve ser rejeitado."""
    login = client.post("/api/auth/login", json={
        "email": "sara@paodeamao.com",
        "senha": "senha123",
    })
    token = login.json()["access_token"]

    # Desativa o usuário diretamente no banco de teste
    usuario_admin.ativo = False
    db_teste.commit()

    response = client.get(
        "/api/admin/categorias",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


# ── Rotas de pedido público com tipo de token errado ─────────────────────────

def test_rota_pedido_publico_com_token_tipo_access_rejeitado(client, db_teste):
    """Access token de admin (type='access') não deve ser aceito em rotas de cliente."""
    # Cria um cliente no banco para garantir um ID válido
    cliente = Cliente(nome="Teste", telefone="81000000001")
    db_teste.add(cliente)
    db_teste.commit()

    token_access = criar_access_token(user_id=cliente.id)

    response = client.post(
        "/api/pedidos",
        json={
            "tipo": "retirada",
            "metodo_pagamento": "pix",
            "itens": [{"produto_id": 1, "quantidade": 1}],
        },
        headers={"Authorization": f"Bearer {token_access}"},
    )
    # Deve falhar na validação de tipo do token (401), não chegar à lógica de negócio
    assert response.status_code == 401


def test_rota_pedido_publico_com_token_refresh_rejeitado(client):
    """Refresh token não deve ser aceito em rotas de cliente."""
    token_refresh = criar_refresh_token(user_id=1)

    response = client.post(
        "/api/pedidos",
        json={
            "tipo": "retirada",
            "metodo_pagamento": "pix",
            "itens": [{"produto_id": 1, "quantidade": 1}],
        },
        headers={"Authorization": f"Bearer {token_refresh}"},
    )
    assert response.status_code == 401
