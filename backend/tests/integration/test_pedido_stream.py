"""
Testes de integração para GET /api/admin/pedidos/stream (SSE).

Cobertura aqui:
  - Auth: 401/422 sem token, token inválido, expirado, tipo errado.

Cobertura via unit tests:
  - tests/unit/test_pedido_pubsub.py cobre: subscribe, unsubscribe, notify,
    queue cheia, múltiplos subscribers, sem loop, após unsubscribe.

Por que os testes de stream body (event: connected, novo-pedido) não ficam aqui:
  Starlette.TestClient coleta o response body de forma síncrona antes de retornar
  o contexto — uma stream SSE infinita nunca termina, bloqueando o processo
  indefinidamente. Testar SSE body requer um servidor HTTP real (uvicorn em thread)
  ou uma suite separada com anyio/asyncio. Adicionado ao backlog como
  'chore/test-sse-live-server'. Ver docs/decisions/sse-test-limitations.md.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from jose import jwt

from app.config import settings


# ── Helpers ───────────────────────────────────────────────────────────────────
def _token_acesso(user_id: int = 1) -> str:
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _token_refresh(user_id: int = 1) -> str:
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _token_expirado(user_id: int = 1) -> str:
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ── Testes de autenticação ────────────────────────────────────────────────────
# A validação do token acontece ANTES de abrir a stream SSE.
# O endpoint retorna 401/422 imediatamente — sem bloqueio no body.

class TestStreamAutenticacao:
    def test_sem_token_retorna_422(self, client):
        """Query param 'token' é obrigatório (FastAPI valida via Depends)."""
        res = client.get("/api/admin/pedidos/stream")
        assert res.status_code == 422

    def test_token_invalido_retorna_401(self, client):
        """JWT malformado → 401 antes de abrir stream."""
        res = client.get("/api/admin/pedidos/stream?token=naoejwt")
        assert res.status_code == 401

    def test_token_expirado_retorna_401(self, client, usuario_admin):
        """Token com exp no passado → 401."""
        token = _token_expirado(usuario_admin.id)
        res = client.get(f"/api/admin/pedidos/stream?token={token}")
        assert res.status_code == 401

    def test_token_refresh_retorna_401(self, client, usuario_admin):
        """Refresh token (type='refresh') não deve ser aceito — somente 'access'."""
        token = _token_refresh(usuario_admin.id)
        res = client.get(f"/api/admin/pedidos/stream?token={token}")
        assert res.status_code == 401


# ── Testes de stream body — SKIPPED (limitação do TestClient) ────────────────

class TestStreamEventos:
    @pytest.mark.skip(
        reason=(
            "TestClient coleta response body de forma síncrona — SSE infinita bloqueia. "
            "Comportamento coberto por tests/unit/test_pedido_pubsub.py. "
            "Para testar body SSE, usar servidor uvicorn real: chore/test-sse-live-server."
        )
    )
    def test_content_type_e_evento_connected(self, client, usuario_admin):
        pass  # placeholder — lógica real no backlog

    @pytest.mark.skip(
        reason=(
            "Mesma limitação: TestClient + SSE infinita = hang. "
            "Ver test_content_type_e_evento_connected."
        )
    )
    def test_evento_novo_pedido_via_queue_direta(self, client, usuario_admin):
        pass
