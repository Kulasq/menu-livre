"""
backend/app/services/pedido_pubsub.py

Pubsub em memória para notificação em tempo real de novos pedidos via SSE.

Funciona com uvicorn single-worker (--workers 1) — confirmado em
deploy/cardapio.service. Com múltiplos workers, migrar para Redis pubsub.

Fluxo:
  1. FastAPI startup chama attach_loop() com o event loop assíncrono.
  2. Quando um pedido é criado (código síncrono), notify() usa
     call_soon_threadsafe() para enfileirar na thread do event loop.
  3. O endpoint /stream lê da queue assíncrona e emite SSE para o cliente.

Limitações / riscos:
  - Queue com maxsize=100: se o consumidor SSE estiver lento e 100 pedidos
    chegarem sem serem consumidos, put_nowait() levanta QueueFull e o evento
    é descartado silenciosamente (failsafe no notify).
  - _loop não é thread-safe de por si — mas call_soon_threadsafe é exatamente
    a API projetada para esse bridge sync→async (ver docs do asyncio).
  - Se o lifespan não chamar attach_loop(), notify() é no-op silencioso.
"""

from __future__ import annotations

import asyncio
from typing import Set

_subscribers: Set[asyncio.Queue] = set()
_loop: asyncio.AbstractEventLoop | None = None


def attach_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Captura o event loop do FastAPI no startup. Chamar exatamente uma vez."""
    global _loop
    _loop = loop


def subscribe() -> asyncio.Queue:
    """
    Registra um novo consumidor SSE.
    Retorna uma Queue assíncrona que receberá payloads de novos pedidos.
    maxsize=100 evita acúmulo ilimitado em caso de consumidor travado.
    """
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    """Remove o consumidor ao desconectar. Chamado no bloco finally do gerador SSE."""
    _subscribers.discard(q)


def notify(payload: dict) -> None:
    """
    Enfileira payload em todos os consumidores registrados.
    Seguro para chamar de código síncrono (pedido_service).

    Falha silenciosa em dois casos:
      - _loop não anexado (startup não chamou attach_loop)
      - Queue cheia (consumidor SSE desconectado sem cleanup)
    """
    if _loop is None:
        return

    for q in list(_subscribers):  # cópia para evitar mutação durante iteração
        try:
            _loop.call_soon_threadsafe(q.put_nowait, payload)
        except Exception:
            # QueueFull ou loop fechado — descarta silenciosamente
            pass
