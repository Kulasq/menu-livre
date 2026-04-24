from __future__ import annotations
import pytest
from app.models.configuracao import Configuracao
from app.models.categoria import Categoria
from app.models.produto import Produto


def _setup_produto(client, db_teste, usuario_admin) -> dict:
    r = client.post("/api/auth/login", json={"email": "admin@exemplo.com", "senha": "senha123"})
    token_admin = r.json()["access_token"]
    cat = client.post(
        "/api/admin/categorias",
        json={"nome": "Lanches"},
        headers={"Authorization": f"Bearer {token_admin}"},
    ).json()
    produto = client.post(
        "/api/admin/produtos",
        json={"categoria_id": cat["id"], "nome": "X-Bacon", "preco": 29.90},
        headers={"Authorization": f"Bearer {token_admin}"},
    ).json()
    return produto


def _token_cliente(client) -> str:
    r = client.post("/api/clientes/identificar", json={"telefone": "81999990010", "nome": "Teste"})
    return r.json()["access_token"]


def _configurar_chave_pix(db_teste, chave: str | None = "11999990000"):
    config = db_teste.get(Configuracao, 1)
    if not config:
        config = Configuracao(id=1, nome_loja="Loja Teste", whatsapp="5581999990000")
        db_teste.add(config)
    config.chave_pix = chave
    db_teste.commit()


class TestPedidoPixQr:
    def test_pix_com_chave_retorna_br_code_e_qr(self, client, db_teste, usuario_admin):
        _configurar_chave_pix(db_teste, "11999990000")
        produto = _setup_produto(client, db_teste, usuario_admin)
        token = _token_cliente(client)

        r = client.post(
            "/api/pedidos",
            json={
                "tipo": "retirada",
                "metodo_pagamento": "pix",
                "itens": [{"produto_id": produto["id"], "quantidade": 1}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert r.status_code == 200
        data = r.json()
        assert data["pix_br_code"] is not None
        assert data["pix_qr_code_base64"] is not None
        assert data["pix_qr_code_base64"].startswith("data:image/png;base64,")

    def test_pix_br_code_contem_valor_correto(self, client, db_teste, usuario_admin):
        _configurar_chave_pix(db_teste, "11999990000")
        produto = _setup_produto(client, db_teste, usuario_admin)
        token = _token_cliente(client)

        r = client.post(
            "/api/pedidos",
            json={
                "tipo": "retirada",
                "metodo_pagamento": "pix",
                "itens": [{"produto_id": produto["id"], "quantidade": 1}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        data = r.json()
        # Produto custa 29.90 sem taxa de entrega (retirada)
        assert "29.90" in data["pix_br_code"]

    def test_pix_sem_chave_retorna_null(self, client, db_teste, usuario_admin):
        _configurar_chave_pix(db_teste, None)
        produto = _setup_produto(client, db_teste, usuario_admin)
        token = _token_cliente(client)

        r = client.post(
            "/api/pedidos",
            json={
                "tipo": "retirada",
                "metodo_pagamento": "pix",
                "itens": [{"produto_id": produto["id"], "quantidade": 1}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert r.status_code == 200
        data = r.json()
        assert data["pix_br_code"] is None
        assert data["pix_qr_code_base64"] is None

    def test_pix_sem_config_retorna_null(self, client, db_teste, usuario_admin):
        # Sem nenhuma configuração cadastrada
        produto = _setup_produto(client, db_teste, usuario_admin)
        token = _token_cliente(client)

        r = client.post(
            "/api/pedidos",
            json={
                "tipo": "retirada",
                "metodo_pagamento": "pix",
                "itens": [{"produto_id": produto["id"], "quantidade": 1}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert r.status_code == 200
        data = r.json()
        assert data["pix_br_code"] is None
        assert data["pix_qr_code_base64"] is None

    def test_dinheiro_nao_retorna_qr(self, client, db_teste, usuario_admin):
        _configurar_chave_pix(db_teste, "11999990000")
        produto = _setup_produto(client, db_teste, usuario_admin)
        token = _token_cliente(client)

        r = client.post(
            "/api/pedidos",
            json={
                "tipo": "retirada",
                "metodo_pagamento": "dinheiro",
                "itens": [{"produto_id": produto["id"], "quantidade": 1}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert r.status_code == 200
        data = r.json()
        assert data["pix_br_code"] is None
        assert data["pix_qr_code_base64"] is None

    def test_cartao_nao_retorna_qr(self, client, db_teste, usuario_admin):
        _configurar_chave_pix(db_teste, "11999990000")
        produto = _setup_produto(client, db_teste, usuario_admin)
        token = _token_cliente(client)

        r = client.post(
            "/api/pedidos",
            json={
                "tipo": "retirada",
                "metodo_pagamento": "cartao",
                "itens": [{"produto_id": produto["id"], "quantidade": 1}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert r.status_code == 200
        data = r.json()
        assert data["pix_br_code"] is None
        assert data["pix_qr_code_base64"] is None

    def test_pix_delivery_inclui_taxa_no_valor_do_qr(self, client, db_teste, usuario_admin):
        config = db_teste.get(Configuracao, 1)
        if not config:
            config = Configuracao(id=1, nome_loja="Loja Teste", whatsapp="5581999990000")
            db_teste.add(config)
        config.chave_pix = "11999990000"
        config.taxa_entrega = 5.00
        db_teste.commit()

        produto = _setup_produto(client, db_teste, usuario_admin)
        token = _token_cliente(client)

        r = client.post(
            "/api/pedidos",
            json={
                "tipo": "delivery",
                "endereco_entrega": "Rua Teste, 123",
                "metodo_pagamento": "pix",
                "itens": [{"produto_id": produto["id"], "quantidade": 1}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert r.status_code == 200
        data = r.json()
        # 29.90 + 5.00 = 34.90
        assert "34.90" in data["pix_br_code"]
