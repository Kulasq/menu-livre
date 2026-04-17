from __future__ import annotations
import pytest
from app.models.cliente import Endereco


def _identificar(client, telefone="81999991001", nome="Lucas") -> dict:
    r = client.post("/api/clientes/identificar", json={"telefone": telefone, "nome": nome})
    assert r.status_code == 200
    return r.json()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── GET /api/clientes/{id}/enderecos ──────────────────────────────────────────

def test_listar_enderecos_vazio(client, usuario_admin):
    sessao = _identificar(client)
    cliente_id = sessao["cliente"]["id"]
    token = sessao["access_token"]

    r = client.get(f"/api/clientes/{cliente_id}/enderecos", headers=_headers(token))
    assert r.status_code == 200
    assert r.json() == []


def test_listar_enderecos_retorna_lista(client, db_teste, usuario_admin):
    sessao = _identificar(client)
    cliente_id = sessao["cliente"]["id"]
    token = sessao["access_token"]

    e = Endereco(cliente_id=cliente_id, endereco="Rua das Flores, 42")
    db_teste.add(e)
    db_teste.commit()

    r = client.get(f"/api/clientes/{cliente_id}/enderecos", headers=_headers(token))
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["endereco"] == "Rua das Flores, 42"
    assert data[0]["cliente_id"] == cliente_id


def test_listar_enderecos_sem_token_falha(client, usuario_admin):
    sessao = _identificar(client)
    cliente_id = sessao["cliente"]["id"]

    r = client.get(f"/api/clientes/{cliente_id}/enderecos")
    assert r.status_code == 403  # HTTPBearer retorna 403 quando não há token


def test_listar_enderecos_de_outro_cliente_falha(client, usuario_admin):
    sessao1 = _identificar(client, telefone="81999991002", nome="Ana")
    sessao2 = _identificar(client, telefone="81999991003", nome="Bruno")

    cliente1_id = sessao1["cliente"]["id"]
    token2 = sessao2["access_token"]

    r = client.get(f"/api/clientes/{cliente1_id}/enderecos", headers=_headers(token2))
    assert r.status_code == 403


# ── DELETE /api/clientes/enderecos/{id} ──────────────────────────────────────

def test_deletar_endereco_proprio(client, db_teste, usuario_admin):
    sessao = _identificar(client)
    cliente_id = sessao["cliente"]["id"]
    token = sessao["access_token"]

    e = Endereco(cliente_id=cliente_id, endereco="Rua A, 1")
    db_teste.add(e)
    db_teste.commit()
    db_teste.refresh(e)

    r = client.delete(f"/api/clientes/enderecos/{e.id}", headers=_headers(token))
    assert r.status_code == 204

    r2 = client.get(f"/api/clientes/{cliente_id}/enderecos", headers=_headers(token))
    assert r2.json() == []


def test_deletar_endereco_de_outro_cliente_falha(client, db_teste, usuario_admin):
    sessao1 = _identificar(client, telefone="81999991004", nome="Carol")
    sessao2 = _identificar(client, telefone="81999991005", nome="Davi")

    e = Endereco(cliente_id=sessao1["cliente"]["id"], endereco="Rua B, 2")
    db_teste.add(e)
    db_teste.commit()
    db_teste.refresh(e)

    r = client.delete(
        f"/api/clientes/enderecos/{e.id}",
        headers=_headers(sessao2["access_token"]),
    )
    assert r.status_code == 403


def test_deletar_endereco_sem_token_falha(client, db_teste, usuario_admin):
    sessao = _identificar(client)
    e = Endereco(cliente_id=sessao["cliente"]["id"], endereco="Rua C, 3")
    db_teste.add(e)
    db_teste.commit()
    db_teste.refresh(e)

    r = client.delete(f"/api/clientes/enderecos/{e.id}")
    assert r.status_code == 403


def test_deletar_endereco_inexistente_falha(client, usuario_admin):
    sessao = _identificar(client)
    token = sessao["access_token"]

    r = client.delete("/api/clientes/enderecos/99999", headers=_headers(token))
    assert r.status_code == 404


# ── Auto-save no pedido delivery ─────────────────────────────────────────────

def test_pedido_delivery_autosalva_endereco(client, db_teste, usuario_admin):
    """Após pedido delivery confirmado, endereço aparece na lista do cliente."""
    from app.models.categoria import Categoria
    from app.models.produto import Produto
    from app.models.configuracao import Configuracao

    # garantir config básica
    config = db_teste.get(Configuracao, 1)
    if not config:
        config = Configuracao(
            id=1, nome_loja="Teste", whatsapp="5581999990000",
            taxa_entrega=5.0, pedido_minimo=0,
        )
        db_teste.add(config)
        db_teste.commit()

    cat = Categoria(nome="Lanches")
    db_teste.add(cat)
    db_teste.commit()
    db_teste.refresh(cat)

    prod = Produto(categoria_id=cat.id, nome="X-Burguer", preco=20.0)
    db_teste.add(prod)
    db_teste.commit()
    db_teste.refresh(prod)

    sessao = _identificar(client, telefone="81999991006", nome="Eva")
    cliente_id = sessao["cliente"]["id"]
    token = sessao["access_token"]

    r = client.post(
        "/api/pedidos",
        json={
            "tipo": "delivery",
            "endereco_entrega": "Av. Principal, 100",
            "metodo_pagamento": "pix",
            "itens": [{"produto_id": prod.id, "quantidade": 1}],
        },
        headers=_headers(token),
    )
    assert r.status_code == 200

    r2 = client.get(f"/api/clientes/{cliente_id}/enderecos", headers=_headers(token))
    enderecos = r2.json()
    assert any(e["endereco"] == "Av. Principal, 100" for e in enderecos)
