from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.pedido import Pedido


def obter_resumo(db: Session) -> dict:
    """Retorna resumo de pedidos do dia para o dashboard.

    Agregações feitas em SQL (count/sum + group_by) em vez de carregar todos
    os pedidos do dia e somar em Python — apoiado nos índices de
    pedidos.status / status_pagamento / criado_em.
    """
    hoje = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    do_dia = Pedido.criado_em >= hoje
    ativo = Pedido.status != "cancelado"

    # Contagem por status — sobre TODOS os pedidos do dia (inclui cancelados)
    por_status = {
        status: qtd
        for status, qtd in (
            db.query(Pedido.status, func.count(Pedido.id))
            .filter(do_dia)
            .group_by(Pedido.status)
            .all()
        )
    }

    # Totais do dia (exclui cancelados)
    total_vendas, total_pedidos = (
        db.query(func.coalesce(func.sum(Pedido.total), 0.0), func.count(Pedido.id))
        .filter(do_dia, ativo)
        .one()
    )
    ticket_medio = total_vendas / total_pedidos if total_pedidos > 0 else 0

    # Contagem por tipo (exclui cancelados)
    por_tipo = {
        tipo: qtd
        for tipo, qtd in (
            db.query(Pedido.tipo, func.count(Pedido.id))
            .filter(do_dia, ativo)
            .group_by(Pedido.tipo)
            .all()
        )
    }

    # Pagamento (exclui cancelados)
    por_pagamento = {
        sp: qtd
        for sp, qtd in (
            db.query(Pedido.status_pagamento, func.count(Pedido.id))
            .filter(do_dia, ativo)
            .group_by(Pedido.status_pagamento)
            .all()
        )
    }
    pagos = por_pagamento.get("pago", 0)
    pendentes_pgto = por_pagamento.get("pendente", 0)

    # Em andamento (pendente, confirmado, em_preparo, pronto)
    em_andamento = (
        db.query(func.count(Pedido.id))
        .filter(
            do_dia,
            Pedido.status.in_(("pendente", "confirmado", "em_preparo", "pronto")),
        )
        .scalar()
        or 0
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
