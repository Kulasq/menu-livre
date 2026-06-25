from __future__ import annotations

import uuid


def obter_token(client, usuario_admin) -> str:
    response = client.post("/api/auth/login", json={
        "email": "admin@exemplo.com",
        "senha": "senha123",
    })
    return response.json()["access_token"]


def _telefone_unico() -> str:
    """Gera um telefone único para evitar conflito entre testes."""
    return f"819{uuid.uuid4().int % 100_000_000:08d}"


def criar_pedido_teste(client, token, preco=25.0):
    """Helper: cria categoria + produto + cliente + pedido."""
    headers = {"Authorization": f"Bearer {token}"}

    cat = client.post(
        "/api/admin/categorias",
        json={"nome": "Hambúrgueres"},
        headers=headers,
    ).json()
    assert "id" in cat, f"Falha ao criar categoria: {cat}"

    prod = client.post(
        "/api/admin/produtos",
        json={"categoria_id": cat["id"], "nome": "X-Burguer", "preco": preco},
        headers=headers,
    ).json()
    assert "id" in prod, f"Falha ao criar produto: {prod}"

    # Telefone único por chamada — evita colisão entre testes
    cliente_res = client.post(
        "/api/clientes/identificar",
        json={"telefone": _telefone_unico(), "nome": "Teste"},
    ).json()
    assert "access_token" in cliente_res, f"Endpoint /clientes/identificar retornou: {cliente_res}"

    cliente_token = cliente_res["access_token"]  # o endpoint usa "access_token", não "token"

    pedido_res = client.post(
        "/api/pedidos",
        json={
            "tipo": "retirada",
            "metodo_pagamento": "pix",
            "itens": [{"produto_id": prod["id"], "quantidade": 1}],
        },
        headers={"Authorization": f"Bearer {cliente_token}"},
    ).json()
    assert "pedido" in pedido_res, f"Falha ao criar pedido: {pedido_res}"

    return pedido_res["pedido"]


# ── Dashboard resumo ─────────────────────────────────────────────────────────

def test_resumo_sem_pedidos(client, usuario_admin):
    token = obter_token(client, usuario_admin)

    response = client.get(
        "/api/admin/dashboard/resumo",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_pedidos"] == 0
    assert data["total_vendas"] == 0
    assert data["ticket_medio"] == 0
    assert data["em_andamento"] == 0


def test_resumo_com_pedidos(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    criar_pedido_teste(client, token, preco=30.0)
    criar_pedido_teste(client, token, preco=40.0)

    response = client.get(
        "/api/admin/dashboard/resumo",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_pedidos"] == 2
    assert data["total_vendas"] == 70.0
    assert data["ticket_medio"] == 35.0
    assert data["em_andamento"] == 2
    assert data["por_status"]["pendente"] == 2
    assert data["por_tipo"]["retirada"] == 2


def test_resumo_exclui_cancelados_do_total(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    pedido = criar_pedido_teste(client, token, preco=50.0)

    client.patch(
        f"/api/admin/pedidos/{pedido['id']}/status",
        json={"status": "cancelado"},
        headers=headers,
    )

    response = client.get(
        "/api/admin/dashboard/resumo",
        headers=headers,
    )

    data = response.json()
    assert data["total_pedidos"] == 0  # cancelado não conta
    assert data["total_vendas"] == 0
    assert data["por_status"]["cancelado"] == 1


def test_resumo_usa_dia_brt_nao_utc(client, usuario_admin, db_teste):
    """O corte de 'hoje' segue o dia civil de Brasília (BRT), não meia-noite UTC.

    Um pedido feito 1 segundo antes da meia-noite BRT de hoje é de ONTEM no Brasil
    e NÃO pode aparecer no resumo; um feito exatamente na meia-noite BRT conta.
    Isso fixa o corte no fuso local independente da hora em que o teste roda.
    """
    from datetime import timedelta
    from app.models.pedido import Pedido
    from app.tempo import hoje_brt, inicio_dia_utc

    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    p_hoje = criar_pedido_teste(client, token, preco=30.0)
    p_ontem = criar_pedido_teste(client, token, preco=99.0)

    inicio_hoje_brt = inicio_dia_utc(hoje_brt())  # meia-noite BRT em UTC naive
    db_teste.get(Pedido, p_hoje["id"]).criado_em = inicio_hoje_brt
    db_teste.get(Pedido, p_ontem["id"]).criado_em = inicio_hoje_brt - timedelta(seconds=1)
    db_teste.commit()

    data = client.get("/api/admin/dashboard/resumo", headers=headers).json()
    assert data["total_pedidos"] == 1          # só o de hoje (BRT)
    assert data["total_vendas"] == 30.0        # o de ontem (99.0) ficou de fora


def test_resumo_sem_autenticacao(client):
    response = client.get("/api/admin/dashboard/resumo")
    assert response.status_code == 403


def test_resumo_pagamento(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    headers = {"Authorization": f"Bearer {token}"}

    pedido = criar_pedido_teste(client, token, preco=30.0)

    client.patch(
        f"/api/admin/pedidos/{pedido['id']}/pagamento",
        json={"status_pagamento": "pago"},
        headers=headers,
    )

    response = client.get(
        "/api/admin/dashboard/resumo",
        headers=headers,
    )

    data = response.json()
    assert data["pagos"] == 1
    assert data["pendentes_pagamento"] == 0