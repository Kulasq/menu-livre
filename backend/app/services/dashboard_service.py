from __future__ import annotations

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.pedido import Pedido


def obter_resumo(db: Session) -> dict:
    """Retorna resumo de pedidos do dia para o dashboard."""
    hoje = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    pedidos_hoje = (
        db.query(Pedido)
        .filter(Pedido.criado_em >= hoje)
        .all()
    )

    # Totais do dia (exclui cancelados)
    ativos = [p for p in pedidos_hoje if p.status != "cancelado"]
    total_vendas = sum(p.total for p in ativos)
    total_pedidos = len(ativos)
    ticket_medio = total_vendas / total_pedidos if total_pedidos > 0 else 0

    # Contagem por status
    por_status = {}
    for p in pedidos_hoje:
        por_status[p.status] = por_status.get(p.status, 0) + 1

    # Contagem por tipo
    por_tipo = {}
    for p in ativos:
        por_tipo[p.tipo] = por_tipo.get(p.tipo, 0) + 1

    # Pagamento
    pagos = sum(1 for p in ativos if p.status_pagamento == "pago")
    pendentes_pgto = sum(1 for p in ativos if p.status_pagamento == "pendente")

    # Em andamento (pendente, confirmado, em_preparo, pronto)
    em_andamento = sum(
        1 for p in pedidos_hoje
        if p.status in ("pendente", "confirmado", "em_preparo", "pronto")
    )

    return {
        "total_pedidos": total_pedidos,
        "total_vendas": round(total_vendas, 2),
        "ticket_medio": round(ticket_medio, 2),
        "em_andamento": em_andamento,
        "por_status": por_status,
        "por_tipo": por_tipo,
        "pagos": pagos,
        "pendentes_pagamento": pendentes_pgto,
    }