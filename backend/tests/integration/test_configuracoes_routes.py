from __future__ import annotations
import pytest


def obter_token(client, usuario_admin) -> str:
    r = client.post("/api/auth/login", json={
        "email": "sara@paodeamao.com",
        "senha": "senha123",
    })
    return r.json()["access_token"]


# ── GET /api/admin/configuracoes ──────────────────────────────────────────────

def test_obter_configuracoes_sem_token(client):
    r = client.get("/api/admin/configuracoes")
    assert r.status_code == 403


def test_obter_configuracoes_cria_defaults(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    r = client.get("/api/admin/configuracoes", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["nome_loja"] == "Pão de Mão"
    assert data["fechado_manualmente"] is False
    assert data["aceitar_agendamentos"] is True
    assert data["taxa_entrega"] == 0.0


# ── PUT /api/admin/configuracoes ──────────────────────────────────────────────

def test_atualizar_configuracoes_sem_token(client):
    r = client.put("/api/admin/configuracoes", json={"nome_loja": "Teste"})
    assert r.status_code == 403


def test_atualizar_campos_simples(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    r = client.put(
        "/api/admin/configuracoes",
        json={"whatsapp": "81999990000", "taxa_entrega": 5.0, "nome_loja": "Pão de Mão Atualizado"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["whatsapp"] == "81999990000"
    assert data["taxa_entrega"] == 5.0
    assert data["nome_loja"] == "Pão de Mão Atualizado"


def test_atualizar_fechado_manualmente(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    r = client.put(
        "/api/admin/configuracoes",
        json={"fechado_manualmente": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["fechado_manualmente"] is True


def test_atualizar_horarios(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    horarios = {
        "domingo": {"aberto": True,  "horarios": [{"inicio": "19:00", "fim": "23:00"}]},
        "segunda": {"aberto": True,  "horarios": [{"inicio": "19:30", "fim": "23:00"}]},
        "terca":   {"aberto": False, "horarios": []},
        "quarta":  {"aberto": False, "horarios": []},
        "quinta":  {"aberto": False, "horarios": []},
        "sexta":   {"aberto": True,  "horarios": [{"inicio": "19:00", "fim": "23:00"}]},
        "sabado":  {"aberto": True,  "horarios": [{"inicio": "19:00", "fim": "23:00"}]},
    }
    r = client.put(
        "/api/admin/configuracoes",
        json={"horarios": horarios},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["horarios"]["domingo"]["aberto"] is True
    assert data["horarios"]["terca"]["aberto"] is False
    assert data["horarios"]["segunda"]["horarios"][0]["inicio"] == "19:30"


def test_atualizar_persiste_entre_requests(client, usuario_admin):
    """Garante que o PUT persiste e o GET seguinte reflete a mudança."""
    token = obter_token(client, usuario_admin)
    client.put(
        "/api/admin/configuracoes",
        json={"pedido_minimo": 20.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    r = client.get("/api/admin/configuracoes", headers={"Authorization": f"Bearer {token}"})
    assert r.json()["pedido_minimo"] == 20.0


# ── GET /api/configuracao (público) ──────────────────────────────────────────

def test_configuracao_publica_sem_autenticacao(client):
    """Endpoint público não requer token."""
    r = client.get("/api/configuracao")
    assert r.status_code == 200


def test_configuracao_publica_contem_campo_aberto(client):
    r = client.get("/api/configuracao")
    assert r.status_code == 200
    data = r.json()
    assert "aberto" in data
    assert isinstance(data["aberto"], bool)


def test_configuracao_publica_fechada_quando_flag_false(client, usuario_admin):
    token = obter_token(client, usuario_admin)
    client.put(
        "/api/admin/configuracoes",
        json={"fechado_manualmente": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    r = client.get("/api/configuracao")
    assert r.json()["aberto"] is False


def test_configuracao_publica_nao_expoe_dados_sensiveis(client):
    """O endpoint público não deve expor campos administrativos."""
    r = client.get("/api/configuracao")
    data = r.json()
    assert "id" not in data
    assert "atualizado_em" not in data
