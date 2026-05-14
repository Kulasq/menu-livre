"""
Testes unitários para app.services.pedido_pubsub.

Cobrem:
  - subscribe / unsubscribe básico
  - notify entrega payload para todos os subscribers
  - notify é no-op quando _loop não está anexado
  - notify descarta silenciosamente se a queue estiver cheia
  - múltiplos subscribers recebem o mesmo payload
  - unsubscribe evita entrega após desconexão
"""
from __future__ import annotations

import asyncio
import pytest

import app.services.pedido_pubsub as pubsub


# ── Fixture: reseta estado global entre testes ────────────────────────────────
@pytest.fixture(autouse=True)
def _reset():
    """Garante estado limpo a cada teste."""
    pubsub._subscribers.clear()
    pubsub._loop = None
    yield
    pubsub._subscribers.clear()
    pubsub._loop = None


# ── Helpers ───────────────────────────────────────────────────────────────────
def _novo_loop():
    loop = asyncio.new_event_loop()
    pubsub.attach_loop(loop)
    return loop


# ── Testes ────────────────────────────────────────────────────────────────────

class TestSubscribeUnsubscribe:
    def test_subscribe_adiciona_queue(self):
        q = pubsub.subscribe()
        assert q in pubsub._subscribers

    def test_unsubscribe_remove_queue(self):
        q = pubsub.subscribe()
        pubsub.unsubscribe(q)
        assert q not in pubsub._subscribers

    def test_unsubscribe_inexistente_nao_levanta(self):
        """discard() em elemento ausente deve ser silencioso."""
        q = asyncio.Queue()
        pubsub.unsubscribe(q)  # não deve levantar

    def test_multiplos_subscribers(self):
        q1 = pubsub.subscribe()
        q2 = pubsub.subscribe()
        assert len(pubsub._subscribers) == 2
        pubsub.unsubscribe(q1)
        assert len(pubsub._subscribers) == 1
        assert q2 in pubsub._subscribers


class TestNotify:
    def test_notify_sem_loop_e_noop(self):
        """Sem attach_loop(), notify() deve ser silencioso."""
        q = pubsub.subscribe()
        pubsub.notify({"id": 1})  # não deve levantar
        assert q.empty()  # nada enfileirado

    def test_notify_entrega_payload(self):
        loop = _novo_loop()
        try:
            q = pubsub.subscribe()
            payload = {"id": 42, "numero": "#0042"}

            pubsub.notify(payload)
            # Executa os callbacks agendados pelo call_soon_threadsafe
            loop.run_until_complete(asyncio.sleep(0))

            assert not q.empty()
            assert q.get_nowait() == payload
        finally:
            loop.close()

    def test_notify_multiplos_subscribers_recebem(self):
        loop = _novo_loop()
        try:
            q1 = pubsub.subscribe()
            q2 = pubsub.subscribe()
            payload = {"id": 10}

            pubsub.notify(payload)
            loop.run_until_complete(asyncio.sleep(0))

            assert q1.get_nowait() == payload
            assert q2.get_nowait() == payload
        finally:
            loop.close()

    def test_notify_apos_unsubscribe_nao_entrega(self):
        loop = _novo_loop()
        try:
            q = pubsub.subscribe()
            pubsub.unsubscribe(q)

            pubsub.notify({"id": 5})
            loop.run_until_complete(asyncio.sleep(0))

            assert q.empty()
        finally:
            loop.close()

    def test_notify_queue_cheia_descarta_silenciosamente(self):
        """Queue com maxsize=1 — second put deve ser descartado sem exceção."""
        loop = _novo_loop()
        try:
            q = asyncio.Queue(maxsize=1)
            pubsub._subscribers.add(q)

            pubsub.notify({"id": 1})
            loop.run_until_complete(asyncio.sleep(0))
            # Queue agora está cheia (maxsize=1)

            # Segundo notify deve descartar silenciosamente
            pubsub.notify({"id": 2})
            loop.run_until_complete(asyncio.sleep(0))

            # Apenas o primeiro chegou
            assert q.get_nowait()["id"] == 1
            assert q.empty()
        finally:
            loop.close()

    def test_notify_sem_subscribers_nao_levanta(self):
        loop = _novo_loop()
        try:
            pubsub.notify({"id": 99})  # sem subscribers
            loop.run_until_complete(asyncio.sleep(0))
        finally:
            loop.close()
