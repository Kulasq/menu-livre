from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from app.models.pedido import Pedido, PedidoItem, PedidoItemModificador
from app.models.produto import Produto
from app.models.cliente import Cliente
from app.models.modificador import Modificador
from app.models.configuracao import Configuracao
from app.schemas.pedido import PedidoCreate, PedidoStatusUpdate, PedidoPagamentoUpdate
from app.services.whatsapp_service import formatar_mensagem, gerar_url
from app.services.configuracao_service import verificar_loja_aberta, calcular_proxima_abertura

_TRANSICOES = {
    "pendente": {"confirmado", "cancelado"},
    "confirmado": {"em_preparo", "cancelado"},
    "em_preparo": {"pronto"},
    "pronto": {"entregue"},
    "entregue": set(),
    "cancelado": set(),
}


def _numero_pedido(db: Session) -> str:
    ultimo = db.query(Pedido).order_by(Pedido.id.desc()).first()
    proximo = 1 if not ultimo else ultimo.id + 1
    return f"PDM-{proximo:04d}"


def criar_pedido(dados: PedidoCreate, cliente_id: int, db: Session) -> dict:
    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    if dados.tipo == "delivery" and not dados.endereco_entrega:
        raise HTTPException(
            status_code=400,
            detail="Endereço de entrega obrigatório para delivery",
        )

    config = db.get(Configuracao, 1)
    taxa_entrega = config.taxa_entrega if config and dados.tipo == "delivery" else 0.0

    # ── Verificar status da loja e regras de agendamento ─────────────────────
    agendado_para = dados.agendado_para  # pode vir do cliente ou ser calculado abaixo

    if config:
        loja_aberta = verificar_loja_aberta(config)

        if not loja_aberta:
            if config.fechado_manualmente:
                raise HTTPException(
                    status_code=400,
                    detail=config.mensagem_fechado or "A loja está fechada no momento.",
                )

            # Fechada por horário — verificar se aceita agendamentos
            if not config.aceitar_agendamentos:
                raise HTTPException(
                    status_code=400,
                    detail=config.mensagem_fechado or "A loja está fechada no momento.",
                )

            # Verificar limite de pedidos agendados pendentes
            if config.limite_agendamentos > 0:
                agendamentos_abertos = db.query(Pedido).filter(
                    Pedido.agendado_para.isnot(None),
                    Pedido.status.in_(["pendente", "confirmado"]),
                ).count()
                if agendamentos_abertos >= config.limite_agendamentos:
                    raise HTTPException(
                        status_code=400,
                        detail="Limite de pedidos agendados atingido. Tente novamente mais tarde.",
                    )

            # Calcular próxima abertura se o cliente não forneceu data
            if not agendado_para:
                agendado_para = calcular_proxima_abertura(config)

    subtotal = 0.0
    itens_db = []

    for item_data in dados.itens:
        if not item_data.produto_id:
            raise HTTPException(status_code=400, detail="produto_id é obrigatório")

        produto = db.get(Produto, item_data.produto_id)
        if not produto or not produto.disponivel:
            raise HTTPException(
                status_code=400,
                detail=f"Produto {item_data.produto_id} indisponível",
            )

        preco_base = produto.preco

        # Verificar modificadores obrigatórios
        for grupo in produto.grupos_modificadores:
            if grupo.obrigatorio:
                ids_grupo = {m.id for m in grupo.modificadores}
                selecionados = {
                    m.modificador_id for m in item_data.modificadores
                    if m.modificador_id in ids_grupo
                }
                if len(selecionados) < grupo.selecao_minima:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Grupo '{grupo.nome}' requer pelo menos {grupo.selecao_minima} opção(ões)",
                    )

        preco_total = preco_base
        mods_db = []

        for mod_data in item_data.modificadores:
            mod = db.get(Modificador, mod_data.modificador_id)
            if not mod or not mod.disponivel:
                raise HTTPException(
                    status_code=400,
                    detail=f"Modificador {mod_data.modificador_id} indisponível",
                )
            preco_total += mod.preco_adicional
            mods_db.append(PedidoItemModificador(
                modificador_id=mod.id,
                nome_snapshot=mod.nome,
                preco_snapshot=mod.preco_adicional,
            ))

        item_subtotal = preco_total * item_data.quantidade
        subtotal += item_subtotal

        # Controle de estoque
        if produto.controle_estoque:
            if produto.estoque_atual < item_data.quantidade:
                raise HTTPException(
                    status_code=400,
                    detail=f"Estoque insuficiente para '{produto.nome}'",
                )
            produto.estoque_atual -= item_data.quantidade
            if produto.estoque_atual == 0:
                produto.disponivel = False

        nome_snapshot = produto.nome
        itens_db.append(PedidoItem(
            produto_id=produto.id,
            variante_id=item_data.variante_id,
            nome_snapshot=nome_snapshot,
            preco_snapshot=preco_total,
            quantidade=item_data.quantidade,
            subtotal=item_subtotal,
            observacao=item_data.observacao,
            modificadores=mods_db,
        ))

    if config and config.pedido_minimo > 0 and subtotal < config.pedido_minimo:
        raise HTTPException(
            status_code=400,
            detail=f"Pedido mínimo é R$ {config.pedido_minimo:.2f}",
        )

    total = subtotal + taxa_entrega
    numero = _numero_pedido(db)

    pedido = Pedido(
        numero=numero,
        cliente_id=cliente_id,
        tipo=dados.tipo,
        status="pendente",
        endereco_entrega=dados.endereco_entrega,
        subtotal=subtotal,
        taxa_entrega=taxa_entrega,
        total=total,
        metodo_pagamento=dados.metodo_pagamento,
        status_pagamento="pendente",
        observacao=dados.observacao,
        agendado_para=agendado_para,
        itens=itens_db,
    )

    db.add(pedido)
    db.commit()

    # Recarregar com todos os relacionamentos para a mensagem WhatsApp
    pedido_completo = _obter_pedido_completo(pedido.id, db)

    # Atualizar stats do cliente
    cliente.total_pedidos += 1
    cliente.total_gasto += total
    cliente.ultimo_pedido = datetime.now(timezone.utc)
    db.commit()

    mensagem = formatar_mensagem(pedido_completo)
    url = gerar_url(mensagem)

    return {
        "pedido": pedido_completo,
        "mensagem_whatsapp": mensagem,
        "whatsapp_url": url,
    }


def obter_pedido(pedido_id: int, db: Session) -> Pedido:
    return _obter_pedido_completo(pedido_id, db)


def listar_pedidos(
    db: Session,
    status: str | None = None,
    tipo: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> list[Pedido]:
    q = db.query(Pedido).options(joinedload(Pedido.cliente)).order_by(Pedido.criado_em.desc())
    if status:
        q = q.filter(Pedido.status == status)
    if tipo:
        q = q.filter(Pedido.tipo == tipo)
    return q.offset((page - 1) * page_size).limit(page_size).all()


def atualizar_status(pedido_id: int, dados: PedidoStatusUpdate, db: Session) -> Pedido:
    pedido = _obter_pedido_completo(pedido_id, db)
    if dados.status not in _TRANSICOES.get(pedido.status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Transição inválida: {pedido.status} → {dados.status}",
        )
    pedido.status = dados.status
    pedido.atualizado_em = datetime.now(timezone.utc)
    db.commit()
    return _obter_pedido_completo(pedido_id, db)


def atualizar_pagamento(pedido_id: int, dados: PedidoPagamentoUpdate, db: Session) -> Pedido:
    pedido = _obter_pedido_completo(pedido_id, db)
    pedido.status_pagamento = dados.status_pagamento
    db.commit()
    return _obter_pedido_completo(pedido_id, db)


def _obter_pedido_completo(pedido_id: int, db: Session) -> Pedido:
    pedido = (
        db.query(Pedido)
        .options(
            joinedload(Pedido.cliente),
            joinedload(Pedido.itens).joinedload(PedidoItem.modificadores),
        )
        .filter(Pedido.id == pedido_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido