from __future__ import annotations


def obter_token(client, usuario_admin) -> str:
    return client.post("/api/auth/login", json={
        "email": "admin@exemplo.com",
        "senha": "senha123",
    }).json()["access_token"]


def criar_produto_teste(client, token, nome="Debocheddar") -> dict:
    cat = client.post(
        "/api/admin/categorias",
        json={"nome": "Hambúrgueres"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    return client.post(
        "/api/admin/produtos",
        json={"categoria_id": cat["id"], "nome": nome, "preco": 23.0},
        headers={"Authorization": f"Bearer {token}"},
    ).json()


# ── CRUD de grupos autônomos ─────────────────────────────────────────────────

def test_criar_grupo_autonomo(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/admin/grupos-modificadores",
        json={
            "nome": "Molho extra",
            "obrigatorio": False,
            "selecao_minima": 0,
            "selecao_maxima": 2,
            "modificadores": [
                {"nome": "Barbecue", "preco_adicional": 2.0},
                {"nome": "Mostarda", "preco_adicional": 1.5},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "Molho extra"
    assert data["obrigatorio"] is False
    assert len(data["modificadores"]) == 2
    # Sem produto_id no response
    assert "produto_id" not in data


def test_listar_grupos_autonomos(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/admin/grupos-modificadores", json={"nome": "G1"}, headers=headers)
    client.post("/api/admin/grupos-modificadores", json={"nome": "G2"}, headers=headers)

    response = client.get("/api/admin/grupos-modificadores", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all("total_produtos" in g for g in data)


def test_atualizar_grupo_autonomo(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    grupo = client.post(
        "/api/admin/grupos-modificadores",
        json={"nome": "Ponto", "obrigatorio": False},
        headers=headers,
    ).json()

    response = client.put(
        f"/api/admin/grupos-modificadores/{grupo['id']}",
        json={"nome": "Ponto (obrigatório)", "obrigatorio": True},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["obrigatorio"] is True


def test_deletar_grupo_autonomo(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    grupo = client.post(
        "/api/admin/grupos-modificadores",
        json={"nome": "Para deletar"},
        headers=headers,
    ).json()

    resp = client.delete(f"/api/admin/grupos-modificadores/{grupo['id']}", headers=headers)
    assert resp.status_code == 204

    lista = client.get("/api/admin/grupos-modificadores", headers=headers).json()
    assert not any(g["id"] == grupo["id"] for g in lista)


def test_deletar_grupo_inexistente(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    resp = client.delete(
        "/api/admin/grupos-modificadores/999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ── Vincular grupo a produtos ────────────────────────────────────────────────

def test_vincular_todos_os_produtos(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    prod1 = criar_produto_teste(client, token, "Burger A")
    prod2 = criar_produto_teste(client, token, "Burger B")
    grupo = client.post(
        "/api/admin/grupos-modificadores",
        json={"nome": "Molho extra"},
        headers=headers,
    ).json()

    resp = client.post(
        f"/api/admin/grupos-modificadores/{grupo['id']}/vincular",
        json={"modo": "todos"},
        headers=headers,
    )

    assert resp.status_code == 200
    assert resp.json()["vinculados"] == 2

    # Confirma que os produtos carregam o grupo
    produtos = client.get("/api/admin/produtos", headers=headers).json()
    for p in [prod1, prod2]:
        p_atualizado = next(x for x in produtos if x["id"] == p["id"])
        assert any(g["id"] == grupo["id"] for g in p_atualizado["grupos_modificadores"])


def test_vincular_por_categoria(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    prod = criar_produto_teste(client, token)
    cat_id = prod["categoria_id"]

    grupo = client.post(
        "/api/admin/grupos-modificadores",
        json={"nome": "Ponto"},
        headers=headers,
    ).json()

    resp = client.post(
        f"/api/admin/grupos-modificadores/{grupo['id']}/vincular",
        json={"modo": "categoria", "categoria_id": cat_id},
        headers=headers,
    )

    assert resp.status_code == 200
    assert resp.json()["vinculados"] == 1


def test_vincular_produtos_especificos(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    prod1 = criar_produto_teste(client, token, "Produto A")
    prod2 = criar_produto_teste(client, token, "Produto B")
    grupo = client.post(
        "/api/admin/grupos-modificadores",
        json={"nome": "Extra"},
        headers=headers,
    ).json()

    resp = client.post(
        f"/api/admin/grupos-modificadores/{grupo['id']}/vincular",
        json={"modo": "produtos", "produtos_ids": [prod1["id"]]},
        headers=headers,
    )

    assert resp.status_code == 200
    assert resp.json()["vinculados"] == 1

    produtos = client.get("/api/admin/produtos", headers=headers).json()
    p1 = next(x for x in produtos if x["id"] == prod1["id"])
    p2 = next(x for x in produtos if x["id"] == prod2["id"])
    assert any(g["id"] == grupo["id"] for g in p1["grupos_modificadores"])
    assert not any(g["id"] == grupo["id"] for g in p2["grupos_modificadores"])


def test_vincular_duplicata_nao_cria_dois(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    prod = criar_produto_teste(client, token)
    grupo = client.post(
        "/api/admin/grupos-modificadores",
        json={"nome": "Extra"},
        headers=headers,
    ).json()

    client.post(
        f"/api/admin/grupos-modificadores/{grupo['id']}/vincular",
        json={"modo": "todos"},
        headers=headers,
    )
    resp2 = client.post(
        f"/api/admin/grupos-modificadores/{grupo['id']}/vincular",
        json={"modo": "todos"},
        headers=headers,
    )

    assert resp2.status_code == 200
    assert resp2.json()["vinculados"] == 0

    produtos = client.get("/api/admin/produtos", headers=headers).json()
    p = next(x for x in produtos if x["id"] == prod["id"])
    assert sum(1 for g in p["grupos_modificadores"] if g["id"] == grupo["id"]) == 1


def test_vincular_modo_invalido(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    grupo = client.post(
        "/api/admin/grupos-modificadores",
        json={"nome": "Geral"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    resp = client.post(
        f"/api/admin/grupos-modificadores/{grupo['id']}/vincular",
        json={"modo": "invalido"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# ── Desvincular grupo de produto ─────────────────────────────────────────────

def test_desvincular_grupo_de_produto(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    prod = criar_produto_teste(client, token)
    grupo = client.post(
        "/api/admin/grupos-modificadores",
        json={"nome": "Extra"},
        headers=headers,
    ).json()

    client.post(
        f"/api/admin/grupos-modificadores/{grupo['id']}/vincular",
        json={"modo": "todos"},
        headers=headers,
    )

    resp = client.delete(
        f"/api/admin/grupos-modificadores/{grupo['id']}/vinculos/{prod['id']}",
        headers=headers,
    )
    assert resp.status_code == 204

    produtos = client.get("/api/admin/produtos", headers=headers).json()
    p = next(x for x in produtos if x["id"] == prod["id"])
    assert not any(g["id"] == grupo["id"] for g in p["grupos_modificadores"])


def test_desvincular_vinculo_inexistente(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    prod = criar_produto_teste(client, token)
    grupo = client.post(
        "/api/admin/grupos-modificadores",
        json={"nome": "Geral"},
        headers=headers,
    ).json()

    resp = client.delete(
        f"/api/admin/grupos-modificadores/{grupo['id']}/vinculos/{prod['id']}",
        headers=headers,
    )
    assert resp.status_code == 404


# ── Compat: rota legada via produto ──────────────────────────────────────────

def test_criar_grupo_via_produto_compat(client, usuario_admin):
    """A rota legada /produtos/{id}/modificadores ainda funciona."""
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    prod = criar_produto_teste(client, token)
    resp = client.post(
        f"/api/admin/produtos/{prod['id']}/modificadores",
        json={"nome": "Ponto", "obrigatorio": True, "modificadores": [{"nome": "No Ponto"}]},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["nome"] == "Ponto"

    # Grupo deve aparecer no produto
    produtos = client.get("/api/admin/produtos", headers=headers).json()
    p = next(x for x in produtos if x["id"] == prod["id"])
    assert len(p["grupos_modificadores"]) == 1


# ── Sem autenticação ─────────────────────────────────────────────────────────

def test_grupos_sem_token(client):
    assert client.get("/api/admin/grupos-modificadores").status_code == 403
    assert client.post("/api/admin/grupos-modificadores", json={"nome": "X"}).status_code == 403


# ── Cardápio público inclui grupos ───────────────────────────────────────────

def test_cardapio_publico_com_grupos_autonomos(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    prod = criar_produto_teste(client, token)
    grupo = client.post(
        "/api/admin/grupos-modificadores",
        json={"nome": "Ponto", "modificadores": [{"nome": "No Ponto"}]},
        headers=headers,
    ).json()
    client.post(
        f"/api/admin/grupos-modificadores/{grupo['id']}/vincular",
        json={"modo": "todos"},
        headers=headers,
    )

    resp = client.get("/api/cardapio")
    assert resp.status_code == 200
    data = resp.json()
    prod_pub = data["categorias"][0]["produtos"][0]
    assert len(prod_pub["grupos_modificadores"]) == 1
    assert prod_pub["grupos_modificadores"][0]["modificadores"][0]["nome"] == "No Ponto"
