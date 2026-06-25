from __future__ import annotations

from app.models.cliente import Cliente

# O endpoint público POST /api/clientes/lookup consulta um cliente por telefone
# sem nunca criar nada. Telefone novo volta 200 com cliente=null (em vez do 400
# "Nome obrigatório" do /identificar), evitando poluir o console do navegador no
# lookup silencioso do checkout. Telefone existente volta cliente + token.


def test_lookup_telefone_novo_retorna_200_sem_cliente(client):
    r = client.post("/api/clientes/lookup", json={"telefone": "81988887777"})
    assert r.status_code == 200
    body = r.json()
    assert body["cliente"] is None
    assert body["access_token"] is None


def test_lookup_nao_cria_cliente(client, db_teste):
    """Lookup de telefone inexistente não pode persistir nada."""
    antes = db_teste.query(Cliente).count()
    client.post("/api/clientes/lookup", json={"telefone": "81988886666"})
    assert db_teste.query(Cliente).count() == antes


def test_lookup_telefone_existente_retorna_cliente_e_token(client):
    # cria o cliente pelo fluxo real (identificar exige nome p/ novo cadastro)
    cadastro = client.post(
        "/api/clientes/identificar",
        json={"telefone": "81977776666", "nome": "Cliente Lookup"},
    )
    assert cadastro.status_code == 200

    r = client.post("/api/clientes/lookup", json={"telefone": "81977776666"})
    assert r.status_code == 200
    body = r.json()
    assert body["cliente"]["nome"] == "Cliente Lookup"
    assert body["cliente"]["telefone"] == "81977776666"
    assert body["access_token"]  # token de sessão presente


def test_lookup_telefone_malformado_retorna_200_sem_cliente(client):
    """Telefone curto demais não deve gerar 400 — lookup é sempre silencioso."""
    r = client.post("/api/clientes/lookup", json={"telefone": "123"})
    assert r.status_code == 200
    assert r.json()["cliente"] is None


def test_identificar_novo_sem_nome_continua_400(client):
    """Regressão: o submit real (/identificar) deve seguir exigindo nome."""
    r = client.post("/api/clientes/identificar", json={"telefone": "81966665555"})
    assert r.status_code == 400
    assert "nome" in r.json()["detail"].lower()
