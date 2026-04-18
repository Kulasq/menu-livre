from __future__ import annotations
import pytest
from app.models.categoria import Categoria
from app.models.produto import Produto


def obter_token_admin(client, usuario_admin) -> str:
    r = client.post("/api/auth/login", json={
        "email": "admin@exemplo.com",
        "senha": "senha123",
    })
    return r.json()["access_token"]


def identificar_cliente(client) -> dict:
    r = client.post("/api/clientes/identificar", json={
        "telefone": "81999990001",
        "nome": "Lucas",
    })
    assert r.status_code == 200
    return r.json()


def criar_produto_teste(client, db_teste, usuario_admin) -> dict:
    token = obter_token_admin(client, usuario_admin)
    cat = client.post(
        "/api/admin/categorias",
        json={"nome": "Hambúrgueres"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    produto = client.post(
        "/api/admin/produtos",
        json={"categoria_id": cat["id"], "nome": "Bacontentão", "preco": 44.90},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    return produto


# ── Clientes ──────────────────────────────────────────────────────────────────

def test_identificar_cliente_novo(client, usuario_admin):
    r = client.post("/api/clientes/identificar", json={
        "telefone": "81999990001",
        "nome": "Lucas",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["cliente"]["nome"] == "Lucas"
    assert "access_token" in data


def test_identificar_cliente_existente(client, usuario_admin):
    # Primeiro cadastro
    client.post("/api/clientes/identificar", json={
        "telefone": "81999990002",
        "nome": "Maria",
    })
    # Segundo acesso — mesmo telefone
    r = client.post("/api/clientes/identificar", json={
        "telefone": "81999990002",
    })
    assert r.status_code == 200
    assert r.json()["cliente"]["nome"] == "Maria"


def test_identificar_cliente_novo_sem_nome_falha(client, usuario_admin):
    r = client.post("/api/clientes/identificar", json={
        "telefone": "81999990003",
    })
    assert r.status_code == 400


# ── Pedidos ───────────────────────────────────────────────────────────────────

def test_criar_pedido_retirada(client, db_teste, usuario_admin):
    produto = criar_produto_teste(client, db_teste, usuario_admin)
    sessao = identificar_cliente(client)
    token_cliente = sessao["access_token"]

    r = client.post(
        "/api/pedidos",
        json={
            "tipo": "retirada",
            "metodo_pagamento": "pix",
            "itens": [{"produto_id": produto["id"], "quantidade": 1}],
        },
        headers={"Authorization": f"Bearer {token_cliente}"},
    )

    assert r.status_code == 200
    data = r.json()
    assert data["pedido"]["numero"].startswith("ML-")
    assert data["pedido"]["status"] == "pendente"
    assert "whatsapp_url" in data
    assert data["whatsapp_url"].startswith("https://api.whatsapp.com/send/")


def test_criar_pedido_sem_token_falha(client, db_teste, usuario_admin):
    produto = criar_produto_teste(client, db_teste, usuario_admin)

    r = client.post("/api/pedidos", json={
        "tipo": "retirada",
        "metodo_pagamento": "pix",
        "itens": [{"produto_id": produto["id"], "quantidade": 1}],
    })
    assert r.status_code == 403


def test_admin_listar_pedidos(client, db_teste, usuario_admin):
    produto = criar_produto_teste(client, db_teste, usuario_admin)
    sessao = identificar_cliente(client)
    token_cliente = sessao["access_token"]
    token_admin = obter_token_admin(client, usuario_admin)

    # Criar pedido
    client.post(
        "/api/pedidos",
        json={
            "tipo": "retirada",
            "metodo_pagamento": "pix",
            "itens": [{"produto_id": produto["id"], "quantidade": 1}],
        },
        headers={"Authorization": f"Bearer {token_cliente}"},
    )

    # Admin lista pedidos
    r = client.get(
        "/api/admin/pedidos",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_criar_pedido_dinheiro_com_troco(client, db_teste, usuario_admin):
    produto = criar_produto_teste(client, db_teste, usuario_admin)
    sessao = identificar_cliente(client)
    token_cliente = sessao["access_token"]

    r = client.post(
        "/api/pedidos",
        json={
            "tipo": "retirada",
            "metodo_pagamento": "dinheiro",
            "troco_para": 60.0,
            "itens": [{"produto_id": produto["id"], "quantidade": 1}],
        },
        headers={"Authorization": f"Bearer {token_cliente}"},
    )

    assert r.status_code == 200
    data = r.json()
    assert data["pedido"]["troco_para"] == 60.0
    assert "Troco para" in data["mensagem_whatsapp"]


def test_criar_pedido_dinheiro_sem_troco(client, db_teste, usuario_admin):
    produto = criar_produto_teste(client, db_teste, usuario_admin)
    sessao = identificar_cliente(client)
    token_cliente = sessao["access_token"]

    r = client.post(
        "/api/pedidos",
        json={
            "tipo": "retirada",
            "metodo_pagamento": "dinheiro",
            "itens": [{"produto_id": produto["id"], "quantidade": 1}],
        },
        headers={"Authorization": f"Bearer {token_cliente}"},
    )

    assert r.status_code == 200
    data = r.json()
    assert data["pedido"]["troco_para"] is None
    assert "Não precisa de troco" in data["mensagem_whatsapp"]


def test_criar_pedido_dinheiro_troco_menor_que_total_falha(client, db_teste, usuario_admin):
    produto = criar_produto_teste(client, db_teste, usuario_admin)
    sessao = identificar_cliente(client)
    token_cliente = sessao["access_token"]

    r = client.post(
        "/api/pedidos",
        json={
            "tipo": "retirada",
            "metodo_pagamento": "dinheiro",
            "troco_para": 1.0,
            "itens": [{"produto_id": produto["id"], "quantidade": 1}],
        },
        headers={"Authorization": f"Bearer {token_cliente}"},
    )

    assert r.status_code == 400
    assert "troco" in r.json()["detail"].lower()


def test_criar_pedido_pix_ignora_troco_para(client, db_teste, usuario_admin):
    produto = criar_produto_teste(client, db_teste, usuario_admin)
    sessao = identificar_cliente(client)
    token_cliente = sessao["access_token"]

    r = client.post(
        "/api/pedidos",
        json={
            "tipo": "retirada",
            "metodo_pagamento": "pix",
            "troco_para": 100.0,
            "itens": [{"produto_id": produto["id"], "quantidade": 1}],
        },
        headers={"Authorization": f"Bearer {token_cliente}"},
    )

    assert r.status_code == 200
    assert r.json()["pedido"]["troco_para"] is None


def test_admin_atualizar_status_pedido(client, db_teste, usuario_admin):
    produto = criar_produto_teste(client, db_teste, usuario_admin)
    sessao = identificar_cliente(client)
    token_cliente = sessao["access_token"]
    token_admin = obter_token_admin(client, usuario_admin)

    pedido = client.post(
        "/api/pedidos",
        json={
            "tipo": "retirada",
            "metodo_pagamento": "pix",
            "itens": [{"produto_id": produto["id"], "quantidade": 1}],
        },
        headers={"Authorization": f"Bearer {token_cliente}"},
    ).json()["pedido"]

    r = client.patch(
        f"/api/admin/pedidos/{pedido['id']}/status",
        json={"status": "confirmado"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "confirmado"