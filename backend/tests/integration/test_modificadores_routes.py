from __future__ import annotations


def obter_token(client, usuario_admin) -> str:
    response = client.post("/api/auth/login", json={
        "email": "cris@paodeamao.com",
        "senha": "senha123",
    })
    return response.json()["access_token"]


def criar_produto_teste(client, token) -> dict:
    """Helper: cria categoria + produto e retorna o produto."""
    cat = client.post(
        "/api/admin/categorias",
        json={"nome": "Hambúrgueres"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    prod = client.post(
        "/api/admin/produtos",
        json={"categoria_id": cat["id"], "nome": "Debocheddar", "preco": 23.0},
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    return prod


# ── Grupos de Modificadores ──────────────────────────────────────────────────

def test_criar_grupo_modificador(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    produto = criar_produto_teste(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/api/admin/produtos/{produto['id']}/modificadores",
        json={
            "nome": "Ponto da carne",
            "obrigatorio": True,
            "selecao_minima": 1,
            "selecao_maxima": 1,
            "modificadores": [
                {"nome": "Bem Passado", "preco_adicional": 0},
                {"nome": "No Ponto", "preco_adicional": 0},
                {"nome": "Mal Passado", "preco_adicional": 0},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "Ponto da carne"
    assert data["obrigatorio"] is True
    assert len(data["modificadores"]) == 3
    assert data["modificadores"][0]["nome"] == "Bem Passado"


def test_criar_grupo_modificador_produto_inexistente(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/admin/produtos/999/modificadores",
        json={"nome": "Ponto da carne"},
        headers=headers,
    )

    assert response.status_code == 404


def test_criar_grupo_com_ardencia(client, usuario_admin):
    """Caso real: grupo de nível de ardência com preços diferentes."""
    token = obter_token(client, usuario_admin)
    produto = criar_produto_teste(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/api/admin/produtos/{produto['id']}/modificadores",
        json={
            "nome": "Nível de ardência",
            "obrigatorio": False,
            "selecao_minima": 0,
            "selecao_maxima": 1,
            "modificadores": [
                {"nome": "Suave", "preco_adicional": 0},
                {"nome": "Médio", "preco_adicional": 0},
                {"nome": "Forte", "preco_adicional": 2.0},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "Nível de ardência"
    assert data["obrigatorio"] is False
    forte = [m for m in data["modificadores"] if m["nome"] == "Forte"][0]
    assert forte["preco_adicional"] == 2.0


def test_atualizar_grupo_modificador(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    produto = criar_produto_teste(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    grupo = client.post(
        f"/api/admin/produtos/{produto['id']}/modificadores",
        json={"nome": "Ponto da carne", "obrigatorio": False},
        headers=headers,
    ).json()

    response = client.put(
        f"/api/admin/modificadores/{grupo['id']}",
        json={"nome": "Ponto (obrigatório)", "obrigatorio": True},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["nome"] == "Ponto (obrigatório)"
    assert data["obrigatorio"] is True


def test_atualizar_grupo_inexistente(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        "/api/admin/modificadores/999",
        json={"nome": "Novo nome"},
        headers=headers,
    )

    assert response.status_code == 404


def test_deletar_grupo_modificador(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    produto = criar_produto_teste(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    grupo = client.post(
        f"/api/admin/produtos/{produto['id']}/modificadores",
        json={
            "nome": "Ponto da carne",
            "modificadores": [{"nome": "Bem Passado"}],
        },
        headers=headers,
    ).json()

    response = client.delete(
        f"/api/admin/modificadores/{grupo['id']}",
        headers=headers,
    )

    assert response.status_code == 204

    # Verificar que o produto ainda existe e não tem mais o grupo
    prod = client.get(
        f"/api/admin/produtos",
        headers=headers,
    ).json()
    prod_encontrado = [p for p in prod if p["id"] == produto["id"]][0]
    assert len(prod_encontrado["grupos_modificadores"]) == 0


def test_deletar_grupo_inexistente(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete(
        "/api/admin/modificadores/999",
        headers=headers,
    )

    assert response.status_code == 404


# ── Modificadores (opções individuais) ───────────────────────────────────────

def test_criar_modificador_individual(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    produto = criar_produto_teste(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    grupo = client.post(
        f"/api/admin/produtos/{produto['id']}/modificadores",
        json={"nome": "Extras"},
        headers=headers,
    ).json()

    response = client.post(
        f"/api/admin/modificadores/{grupo['id']}/opcoes",
        json={"nome": "Bacon extra", "preco_adicional": 5.0},
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "Bacon extra"
    assert data["preco_adicional"] == 5.0
    assert data["disponivel"] is True


def test_criar_modificador_grupo_inexistente(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/admin/modificadores/999/opcoes",
        json={"nome": "Bacon extra"},
        headers=headers,
    )

    assert response.status_code == 404


def test_atualizar_modificador(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    produto = criar_produto_teste(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    grupo = client.post(
        f"/api/admin/produtos/{produto['id']}/modificadores",
        json={
            "nome": "Extras",
            "modificadores": [{"nome": "Bacon", "preco_adicional": 5.0}],
        },
        headers=headers,
    ).json()

    mod_id = grupo["modificadores"][0]["id"]

    response = client.put(
        f"/api/admin/modificadores/opcoes/{mod_id}",
        json={"nome": "Bacon duplo", "preco_adicional": 8.0},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["nome"] == "Bacon duplo"
    assert data["preco_adicional"] == 8.0


def test_atualizar_modificador_inexistente(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        "/api/admin/modificadores/opcoes/999",
        json={"nome": "Novo"},
        headers=headers,
    )

    assert response.status_code == 404


def test_deletar_modificador(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    produto = criar_produto_teste(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    grupo = client.post(
        f"/api/admin/produtos/{produto['id']}/modificadores",
        json={
            "nome": "Extras",
            "modificadores": [
                {"nome": "Bacon"},
                {"nome": "Ovo"},
            ],
        },
        headers=headers,
    ).json()

    mod_bacon = [m for m in grupo["modificadores"] if m["nome"] == "Bacon"][0]

    response = client.delete(
        f"/api/admin/modificadores/opcoes/{mod_bacon['id']}",
        headers=headers,
    )

    assert response.status_code == 204


def test_deletar_modificador_inexistente(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete(
        "/api/admin/modificadores/opcoes/999",
        headers=headers,
    )

    assert response.status_code == 404


# ── Sem autenticação ─────────────────────────────────────────────────────────

def test_modificadores_sem_token(client):
    response = client.post(
        "/api/admin/produtos/1/modificadores",
        json={"nome": "Ponto"},
    )
    assert response.status_code == 403


# ── Produto carrega com modificadores ────────────────────────────────────────

def test_produto_retorna_modificadores(client, usuario_admin):
    """Verifica que GET /produtos traz os grupos e opções corretamente."""
    token = obter_token(client, usuario_admin)
    produto = criar_produto_teste(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        f"/api/admin/produtos/{produto['id']}/modificadores",
        json={
            "nome": "Ponto da carne",
            "obrigatorio": True,
            "selecao_maxima": 1,
            "modificadores": [
                {"nome": "Bem Passado"},
                {"nome": "No Ponto"},
                {"nome": "Mal Passado"},
            ],
        },
        headers=headers,
    )

    response = client.get("/api/admin/produtos", headers=headers)
    assert response.status_code == 200

    prod = [p for p in response.json() if p["id"] == produto["id"]][0]
    assert len(prod["grupos_modificadores"]) == 1
    assert prod["grupos_modificadores"][0]["nome"] == "Ponto da carne"
    assert len(prod["grupos_modificadores"][0]["modificadores"]) == 3


def test_cardapio_publico_com_modificadores(client, usuario_admin):
    """Verifica que o cardápio público também traz os modificadores."""
    token = obter_token(client, usuario_admin)
    produto = criar_produto_teste(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        f"/api/admin/produtos/{produto['id']}/modificadores",
        json={
            "nome": "Ponto",
            "modificadores": [{"nome": "No Ponto"}],
        },
        headers=headers,
    )

    response = client.get("/api/cardapio")
    assert response.status_code == 200
    data = response.json()

    prod_pub = data["categorias"][0]["produtos"][0]
    assert len(prod_pub["grupos_modificadores"]) == 1
    assert prod_pub["grupos_modificadores"][0]["modificadores"][0]["nome"] == "No Ponto"