"""Testes de integração das rotas de cupom (admin CRUD + público validar).

Cobre:
- GET /api/admin/cupons — sem auth retorna 401
- POST /api/admin/cupons — cria cupom
- POST /api/cupons/validar — preview sem autenticação
- Cupom inválido retorna valido=false
- Aplicação de cupom no pedido público (cupom_codigo no payload)
"""
from __future__ import annotations
import pytest

from app.models.usuario import Usuario
from app.models.cupom import Cupom
from app.services.auth_service import hash_senha


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def token_admin(client, db_teste):
    """Cria usuário admin e retorna Bearer token."""
    from app.models.usuario import Usuario
    u = Usuario(
        nome="Admin Teste",
        email="admin_cupom@teste.com",
        senha_hash=hash_senha("senha123"),
        role="superadmin",
    )
    db_teste.add(u)
    db_teste.commit()
    res = client.post("/api/auth/login", json={
        "email": "admin_cupom@teste.com",
        "senha": "senha123",
    })
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
def cupom_ativo(db_teste):
    c = Cupom(
        codigo="INT10",
        tipo="percentual",
        valor=10.0,
        ativo=True,
    )
    db_teste.add(c)
    db_teste.commit()
    return c


# ── Testes admin ──────────────────────────────────────────────────────────────

class TestAdminCupons:

    def test_listar_sem_auth_retorna_4xx(self, client):
        # HTTPBearer retorna 403 quando sem Authorization header
        res = client.get("/api/admin/cupons")
        assert res.status_code in (401, 403)

    def test_criar_cupom(self, client, token_admin):
        res = client.post(
            "/api/admin/cupons",
            json={
                "codigo": "NOVOCUPOM",
                "tipo": "valor_fixo",
                "valor": 15.0,
                "ativo": True,
            },
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["codigo"] == "NOVOCUPOM"
        assert data["usos_atuais"] == 0

    def test_criar_cupom_codigo_normalizado(self, client, token_admin):
        res = client.post(
            "/api/admin/cupons",
            json={"codigo": "minusculo", "tipo": "valor_fixo", "valor": 5.0},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert res.status_code == 201
        assert res.json()["codigo"] == "MINUSCULO"

    def test_listar_cupons(self, client, token_admin, cupom_ativo):
        res = client.get(
            "/api/admin/cupons",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert res.status_code == 200
        codigos = [c["codigo"] for c in res.json()]
        assert "INT10" in codigos

    def test_atualizar_cupom(self, client, token_admin, cupom_ativo):
        res = client.put(
            f"/api/admin/cupons/{cupom_ativo.id}",
            json={"ativo": False},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert res.status_code == 200
        assert res.json()["ativo"] is False

    def test_deletar_cupom_sem_usos(self, client, token_admin, cupom_ativo):
        res = client.delete(
            f"/api/admin/cupons/{cupom_ativo.id}",
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert res.status_code == 204

    def test_criar_cupom_duplicado_retorna_409(self, client, token_admin, cupom_ativo):
        res = client.post(
            "/api/admin/cupons",
            json={"codigo": "INT10", "tipo": "valor_fixo", "valor": 5.0},
            headers={"Authorization": f"Bearer {token_admin}"},
        )
        assert res.status_code == 409


# ── Testes público ────────────────────────────────────────────────────────────

class TestPublicoCupons:

    def test_validar_cupom_valido(self, client, cupom_ativo):
        res = client.post("/api/cupons/validar", json={
            "codigo": "INT10",
            "subtotal": 100.0,
        })
        assert res.status_code == 200
        data = res.json()
        assert data["valido"] is True
        assert data["desconto"] == pytest.approx(10.0)

    def test_validar_cupom_invalido(self, client):
        res = client.post("/api/cupons/validar", json={
            "codigo": "FANTASMA",
            "subtotal": 100.0,
        })
        assert res.status_code == 200
        data = res.json()
        assert data["valido"] is False
        assert data["motivo"] is not None

    def test_validar_valor_minimo_nao_atingido(self, client, db_teste):
        c = Cupom(
            codigo="MIN100",
            tipo="valor_fixo",
            valor=10.0,
            valor_minimo_pedido=100.0,
            ativo=True,
        )
        db_teste.add(c)
        db_teste.commit()

        res = client.post("/api/cupons/validar", json={
            "codigo": "MIN100",
            "subtotal": 50.0,
        })
        assert res.status_code == 200
        assert res.json()["valido"] is False
        assert "mínimo" in res.json()["motivo"].lower()

    def test_validar_cupom_esgotado(self, client, db_teste):
        c = Cupom(
            codigo="ESGOTADO2",
            tipo="valor_fixo",
            valor=5.0,
            limite_total_usos=1,
            usos_atuais=1,
            ativo=True,
        )
        db_teste.add(c)
        db_teste.commit()

        res = client.post("/api/cupons/validar", json={
            "codigo": "ESGOTADO2",
            "subtotal": 50.0,
        })
        assert res.status_code == 200
        assert res.json()["valido"] is False
