from __future__ import annotations
import pytest
from app.models.categoria import Categoria
from app.models.produto import Produto
from app.services.auth_service import hash_senha
from app.models.usuario import Usuario


def _criar_admin(db_teste):
    u = db_teste.query(Usuario).filter(Usuario.email == "admin@exemplo.com").first()
    if not u:
        u = Usuario(nome="Admin", email="admin@exemplo.com",
                    senha_hash=hash_senha("senha123"), role="superadmin")
        db_teste.add(u)
        db_teste.commit()
    return u


def _token_admin(client):
    r = client.post("/api/auth/login", json={"email": "admin@exemplo.com", "senha": "senha123"})
    return r.json()["access_token"]


def _identificar(client, tel="81988880001", nome="Ana"):
    r = client.post("/api/clientes/identificar", json={"telefone": tel, "nome": nome})
    assert r.status_code == 200
    d = r.json()
    return d["cliente"]["id"], d["access_token"]


def _criar_produto(client, db_teste):
    _criar_admin(db_teste)
    tok = _token_admin(client)
    cat = client.post("/api/admin/categorias",
                      json={"nome": "Lanches"},
                      headers={"Authorization": f"Bearer {tok}"}).json()
    prod = client.post("/api/admin/produtos",
                       json={"categoria_id": cat["id"], "nome": "X-Burguer", "preco": 25.0},
                       headers={"Authorization": f"Bearer {tok}"}).json()
    return prod


def _fazer_pedido(client, token, produto_id, tipo="retirada"):
    r = client.post(
        "/api/pedidos",
        json={
            "tipo": tipo,
            "metodo_pagamento": "dinheiro",
            "itens": [{"produto_id": produto_id, "quantidade": 1}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()


# ── GET /api/pedidos ──────────────────────────────────────────────────────────

def test_listar_pedidos_requer_autenticacao(client, db_teste):
    r = client.get("/api/pedidos")
    assert r.status_code in (401, 403)


def test_listar_pedidos_vazio(client, db_teste):
    _, tok = _identificar(client)
    r = client.get("/api/pedidos", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json() == []


def test_listar_pedidos_retorna_proprios(client, db_teste):
    produto = _criar_produto(client, db_teste)
    _, tok = _identificar(client, tel="81988880002", nome="Bruno")

    _fazer_pedido(client, tok, produto["id"])
    _fazer_pedido(client, tok, produto["id"])

    r = client.get("/api/pedidos", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    pedidos = r.json()
    assert len(pedidos) == 2
    # mais recente primeiro
    assert pedidos[0]["criado_em"] >= pedidos[1]["criado_em"]


def test_listar_pedidos_nao_retorna_de_outro_cliente(client, db_teste):
    produto = _criar_produto(client, db_teste)
    _, tok_a = _identificar(client, tel="81988880003", nome="Carlos")
    _, tok_b = _identificar(client, tel="81988880004", nome="Diana")

    _fazer_pedido(client, tok_a, produto["id"])

    r = client.get("/api/pedidos", headers={"Authorization": f"Bearer {tok_b}"})
    assert r.status_code == 200
    assert r.json() == []


def test_listar_pedidos_limite(client, db_teste):
    produto = _criar_produto(client, db_teste)
    _, tok = _identificar(client, tel="81988880005", nome="Eduardo")

    for _ in range(3):
        _fazer_pedido(client, tok, produto["id"])

    r = client.get("/api/pedidos?limite=2", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_listar_pedidos_inclui_itens(client, db_teste):
    produto = _criar_produto(client, db_teste)
    _, tok = _identificar(client, tel="81988880006", nome="Fernanda")
    _fazer_pedido(client, tok, produto["id"])

    r = client.get("/api/pedidos", headers={"Authorization": f"Bearer {tok}"})
    pedidos = r.json()
    assert len(pedidos[0]["itens"]) == 1
    assert pedidos[0]["itens"][0]["nome_snapshot"] == "X-Burguer"


# ── Segmento RFM (integração via criar_pedido) ────────────────────────────────

def test_segmento_atualiza_para_novo_apos_primeiro_pedido(client, db_teste):
    from app.models.cliente import Cliente
    produto = _criar_produto(client, db_teste)
    cliente_id, tok = _identificar(client, tel="81988880007", nome="Gabi")

    _fazer_pedido(client, tok, produto["id"])

    cliente = db_teste.get(Cliente, cliente_id)
    db_teste.refresh(cliente)
    assert cliente.segmento == "novo"
    assert cliente.total_pedidos == 1
