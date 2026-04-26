from __future__ import annotations
import pytest
from datetime import datetime, timezone, timedelta

from app.models.cliente import Cliente, Endereco
from app.models.usuario import Usuario
from app.services.auth_service import hash_senha


def _criar_admin(db):
    u = db.query(Usuario).filter(Usuario.email == "admin@exemplo.com").first()
    if not u:
        u = Usuario(nome="Admin", email="admin@exemplo.com",
                    senha_hash=hash_senha("senha123"), role="superadmin")
        db.add(u)
        db.commit()
    return u


def _token_admin(client):
    r = client.post("/api/auth/login", json={"email": "admin@exemplo.com", "senha": "senha123"})
    return r.json()["access_token"]


def _add_cliente(db, nome, telefone, total_pedidos=0, segmento="novo", total_gasto=0.0, dias=None):
    c = Cliente(nome=nome, telefone=telefone)
    c.total_pedidos = total_pedidos
    c.total_gasto = total_gasto
    c.segmento = segmento
    c.ultimo_pedido = datetime.now(timezone.utc) - timedelta(days=dias) if dias is not None else None
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def setup(client, db_teste):
    _criar_admin(db_teste)
    c1 = _add_cliente(db_teste, "Ana Lima", "81911110000", total_pedidos=5, segmento="campeao", total_gasto=250.0, dias=3)
    c2 = _add_cliente(db_teste, "Bruno Costa", "81922220000", total_pedidos=2, segmento="leal", total_gasto=60.0, dias=15)

    e1 = Endereco(cliente_id=c1.id, endereco="Rua das Flores, 10")
    e2 = Endereco(cliente_id=c1.id, endereco="Av. Central, 200")
    db_teste.add_all([e1, e2])
    db_teste.commit()
    return {"c1": c1, "c2": c2}


# ── GET /api/admin/clientes/lista ─────────────────────────────────────────────

def test_lista_requer_auth(client):
    r = client.get("/api/admin/clientes/lista")
    assert r.status_code in (401, 403)


def test_lista_retorna_todos(client, setup):
    tok = _token_admin(client)
    r = client.get("/api/admin/clientes/lista", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert len(data["clientes"]) == 2


def test_lista_busca_por_nome(client, setup):
    tok = _token_admin(client)
    r = client.get("/api/admin/clientes/lista?q=ana", headers={"Authorization": f"Bearer {tok}"})
    data = r.json()
    assert data["total"] == 1
    assert data["clientes"][0]["nome"] == "Ana Lima"


def test_lista_filtro_segmento(client, setup):
    tok = _token_admin(client)
    r = client.get("/api/admin/clientes/lista?segmento=leal", headers={"Authorization": f"Bearer {tok}"})
    data = r.json()
    assert data["total"] == 1
    assert data["clientes"][0]["nome"] == "Bruno Costa"


def test_lista_paginacao(client, setup):
    tok = _token_admin(client)
    r = client.get("/api/admin/clientes/lista?page=1&page_size=1", headers={"Authorization": f"Bearer {tok}"})
    data = r.json()
    assert data["total"] == 2
    assert len(data["clientes"]) == 1


# ── GET /api/admin/clientes/{id} ──────────────────────────────────────────────

def test_detalhe_requer_auth(client, setup):
    r = client.get(f"/api/admin/clientes/{setup['c1'].id}")
    assert r.status_code in (401, 403)


def test_detalhe_cliente_existente(client, setup):
    tok = _token_admin(client)
    r = client.get(f"/api/admin/clientes/{setup['c1'].id}", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    data = r.json()
    assert data["nome"] == "Ana Lima"
    assert data["total_pedidos"] == 5
    assert data["segmento"] == "campeao"
    assert "total_gasto" in data
    assert "nivel_fidelidade" in data


def test_detalhe_cliente_inexistente(client, setup):
    tok = _token_admin(client)
    r = client.get("/api/admin/clientes/99999", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404


# ── GET /api/admin/clientes/{id}/enderecos ────────────────────────────────────

def test_enderecos_requer_auth(client, setup):
    r = client.get(f"/api/admin/clientes/{setup['c1'].id}/enderecos")
    assert r.status_code in (401, 403)


def test_enderecos_cliente_com_enderecos(client, setup):
    tok = _token_admin(client)
    r = client.get(f"/api/admin/clientes/{setup['c1'].id}/enderecos",
                   headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    enderecos = {e["endereco"] for e in data}
    assert "Rua das Flores, 10" in enderecos
    assert "Av. Central, 200" in enderecos


def test_enderecos_cliente_sem_enderecos(client, setup):
    tok = _token_admin(client)
    r = client.get(f"/api/admin/clientes/{setup['c2'].id}/enderecos",
                   headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json() == []


def test_enderecos_cliente_inexistente(client, setup):
    tok = _token_admin(client)
    r = client.get("/api/admin/clientes/99999/enderecos",
                   headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404


# ── GET /api/admin/clientes/{id}/pedidos ─────────────────────────────────────

def test_pedidos_requer_auth(client, setup):
    r = client.get(f"/api/admin/clientes/{setup['c1'].id}/pedidos")
    assert r.status_code in (401, 403)


def test_pedidos_cliente_sem_pedidos(client, setup):
    tok = _token_admin(client)
    r = client.get(f"/api/admin/clientes/{setup['c1'].id}/pedidos",
                   headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json() == []


def test_pedidos_cliente_inexistente(client, setup):
    tok = _token_admin(client)
    r = client.get("/api/admin/clientes/99999/pedidos",
                   headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404


# ── GET /api/admin/clientes (PDV — rota original não quebrou) ─────────────────

def test_busca_pdv_sem_telefone_retorna_vazio(client, setup):
    tok = _token_admin(client)
    r = client.get("/api/admin/clientes", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json() == []


def test_busca_pdv_com_telefone_existente(client, setup):
    tok = _token_admin(client)
    r = client.get("/api/admin/clientes?telefone=81911110000",
                   headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["nome"] == "Ana Lima"


# ── POST /api/admin/clientes (criar) ─────────────────────────────────────────

def test_criar_cliente_requer_auth(client, setup):
    r = client.post("/api/admin/clientes", json={"nome": "Novo", "telefone": "81999000001"})
    assert r.status_code in (401, 403)


def test_criar_cliente_sucesso(client, setup):
    tok = _token_admin(client)
    r = client.post("/api/admin/clientes",
                    json={"nome": "Novo Cliente", "telefone": "81999000001"},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 201
    data = r.json()
    assert data["nome"] == "Novo Cliente"
    assert data["telefone"] == "81999000001"


def test_criar_cliente_telefone_duplicado(client, setup):
    tok = _token_admin(client)
    r = client.post("/api/admin/clientes",
                    json={"nome": "Outro", "telefone": "81911110000"},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 409


def test_criar_cliente_sem_nome_retorna_400(client, setup):
    tok = _token_admin(client)
    r = client.post("/api/admin/clientes",
                    json={"telefone": "81999000002"},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 400


# ── PUT /api/admin/clientes/{id} ─────────────────────────────────────────────

def test_atualizar_cliente_nome(client, setup):
    tok = _token_admin(client)
    r = client.put(f"/api/admin/clientes/{setup['c1'].id}",
                   json={"nome": "Ana Lima Atualizada"},
                   headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json()["nome"] == "Ana Lima Atualizada"


def test_atualizar_cliente_telefone(client, setup):
    tok = _token_admin(client)
    r = client.put(f"/api/admin/clientes/{setup['c1'].id}",
                   json={"telefone": "81955550000"},
                   headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json()["telefone"] == "81955550000"


def test_atualizar_cliente_telefone_duplicado(client, setup):
    tok = _token_admin(client)
    r = client.put(f"/api/admin/clientes/{setup['c1'].id}",
                   json={"telefone": setup['c2'].telefone},
                   headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 409


def test_atualizar_cliente_inexistente(client, setup):
    tok = _token_admin(client)
    r = client.put("/api/admin/clientes/99999",
                   json={"nome": "X"},
                   headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404


# ── DELETE /api/admin/clientes/{id} ──────────────────────────────────────────

def test_excluir_cliente_sucesso(client, setup):
    tok = _token_admin(client)
    r = client.delete(f"/api/admin/clientes/{setup['c2'].id}",
                      headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 204
    # Confirma que sumiu
    r2 = client.get(f"/api/admin/clientes/{setup['c2'].id}",
                    headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 404


def test_excluir_cliente_inexistente(client, setup):
    tok = _token_admin(client)
    r = client.delete("/api/admin/clientes/99999",
                      headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404


def test_excluir_cliente_requer_auth(client, setup):
    r = client.delete(f"/api/admin/clientes/{setup['c1'].id}")
    assert r.status_code in (401, 403)


# ── POST /api/admin/clientes/{id}/enderecos ───────────────────────────────────

def test_adicionar_endereco_sucesso(client, setup):
    tok = _token_admin(client)
    r = client.post(f"/api/admin/clientes/{setup['c2'].id}/enderecos",
                    json={"endereco": "Rua Nova, 42"},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 201
    assert r.json()["endereco"] == "Rua Nova, 42"


def test_adicionar_endereco_cliente_inexistente(client, setup):
    tok = _token_admin(client)
    r = client.post("/api/admin/clientes/99999/enderecos",
                    json={"endereco": "Rua X"},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404


def test_adicionar_endereco_vazio_retorna_400(client, setup):
    tok = _token_admin(client)
    r = client.post(f"/api/admin/clientes/{setup['c1'].id}/enderecos",
                    json={"endereco": "   "},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 400


# ── DELETE /api/admin/clientes/{id}/enderecos/{endereco_id} ──────────────────

def test_excluir_endereco_sucesso(client, setup, db_teste):
    from app.models.cliente import Endereco
    end = db_teste.query(Endereco).filter(Endereco.cliente_id == setup['c1'].id).first()
    tok = _token_admin(client)
    r = client.delete(f"/api/admin/clientes/{setup['c1'].id}/enderecos/{end.id}",
                      headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 204


def test_excluir_endereco_de_outro_cliente(client, setup, db_teste):
    from app.models.cliente import Endereco
    end = db_teste.query(Endereco).filter(Endereco.cliente_id == setup['c1'].id).first()
    tok = _token_admin(client)
    r = client.delete(f"/api/admin/clientes/{setup['c2'].id}/enderecos/{end.id}",
                      headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403
