from __future__ import annotations
from datetime import datetime, date, time, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from app.models.pedido import Pedido, PedidoItem, PedidoItemModificador
from app.models.produto import Produto
from app.models.cliente import Cliente
from app.models.modificador import Modificador
from app.models.configuracao import Configuracao
from app.schemas.pedido import PedidoCreate, PedidoAdminCreate, PedidoStatusUpdate, PedidoPagamentoUpdate
from app.services.whatsapp_service import formatar_mensagem, gerar_url
from app.services.configuracao_service import verificar_loja_aberta, calcular_proxima_abertura
from app.services import cliente_service

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
    return f"ML-{proximo:04d}"


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

    if dados.metodo_pagamento == "dinheiro" and dados.troco_para is not None:
        if dados.troco_para < total:
            raise HTTPException(
                status_code=400,
                detail=f"Troco inválido: valor deve ser maior ou igual ao total (R$ {total:.2f})",
            )

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
        troco_para=dados.troco_para,
        status_pagamento="pendente",
        observacao=dados.observacao,
        agendado_para=agendado_para,
        itens=itens_db,
    )

    db.add(pedido)
    db.commit()

    # Recarregar com todos os relacionamentos para a mensagem WhatsApp
    pedido_completo = _obter_pedido_completo(pedido.id, db)

    # Auto-salvar endereço de delivery — falha silenciosa para não derrubar o pedido
    if dados.tipo == "delivery" and dados.endereco_entrega:
        try:
            cliente_service.salvar_endereco_se_novo(db, cliente_id, dados.endereco_entrega)
        except Exception:
            pass

    # Atualizar stats e segmento do cliente
    cliente.total_pedidos += 1
    cliente.total_gasto += total
    cliente.ultimo_pedido = datetime.now(timezone.utc)
    cliente.segmento = cliente_service.calcular_segmento_rfm(cliente)
    db.commit()

    nome_loja = config.nome_loja if config else "Menu Livre"
    chave_pix = config.chave_pix if config else None
    mensagem = formatar_mensagem(pedido_completo, nome_loja, chave_pix)
    url = gerar_url(mensagem)

    resultado: dict = {
        "pedido": pedido_completo,
        "mensagem_whatsapp": mensagem,
        "whatsapp_url": url,
        "pix_br_code": None,
        "pix_qr_code_base64": None,
    }

    if dados.metodo_pagamento == "pix" and chave_pix:
        from app.services.pix_service import gerar_cobranca_pix
        tipo_chave = config.tipo_chave_pix if config else None
        cobranca = gerar_cobranca_pix(chave_pix, total, nome_loja, tipo_chave=tipo_chave)
        if cobranca:
            resultado["pix_br_code"] = cobranca["br_code"]
            resultado["pix_qr_code_base64"] = cobranca["qr_code_base64"]

    return resultado


def criar_pedido_admin(dados: PedidoAdminCreate, db: Session) -> dict:
    """Cria pedido pelo admin. Bypassa validações de horário/agendamento.
    Mantém validações de estoque e modificadores obrigatórios.
    Não gera URL WhatsApp.
    """
    # ── Resolver cliente ─────────────────────────────────────────────────────
    _BALCAO_TELEFONE = "00000000000"
    if dados.cliente_id:
        cliente = db.get(Cliente, dados.cliente_id)
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
    elif dados.cliente_telefone:
        # Buscar por telefone ou criar novo
        cliente = db.query(Cliente).filter(
            Cliente.telefone == dados.cliente_telefone
        ).first()
        if not cliente:
            cliente = Cliente(
                nome=dados.cliente_nome or "Cliente",
                telefone=dados.cliente_telefone,
            )
            db.add(cliente)
            db.flush()
    else:
        # Sem identificação — usa/cria cliente sistema "Balcão"
        cliente = db.query(Cliente).filter(
            Cliente.telefone == _BALCAO_TELEFONE
        ).first()
        if not cliente:
            cliente = Cliente(nome="Balcão", telefone=_BALCAO_TELEFONE)
            db.add(cliente)
            db.flush()

    cliente_id = cliente.id

    if dados.tipo == "delivery" and not dados.endereco_entrega:
        raise HTTPException(status_code=400, detail="Endereço de entrega obrigatório para delivery")

    config = db.get(Configuracao, 1)
    taxa_entrega = config.taxa_entrega if config and dados.tipo == "delivery" else 0.0

    # ── BYPASS de horário/agendamento (origem=admin) ─────────────────────────
    # Admin pode criar a qualquer hora. Não aplica limite de agendamentos.
    agendado_para = None

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

        itens_db.append(PedidoItem(
            produto_id=produto.id,
            variante_id=item_data.variante_id,
            nome_snapshot=produto.nome,
            preco_snapshot=preco_total,
            quantidade=item_data.quantidade,
            subtotal=item_subtotal,
            observacao=item_data.observacao,
            modificadores=mods_db,
        ))

    total = subtotal + taxa_entrega
    numero = _numero_pedido(db)

    if dados.metodo_pagamento == "dinheiro" and dados.troco_para is not None:
        if dados.troco_para < total:
            raise HTTPException(
                status_code=400,
                detail=f"Troco inválido: valor deve ser maior ou igual ao total (R$ {total:.2f})",
            )

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
        troco_para=dados.troco_para,
        status_pagamento="pendente",
        observacao=dados.observacao,
        nome_cliente_balcao=dados.nome_cliente_balcao if dados.tipo == "balcao" else None,
        agendado_para=agendado_para,
        itens=itens_db,
    )

    db.add(pedido)
    db.commit()

    pedido_completo = _obter_pedido_completo(pedido.id, db)

    # Atualizar stats e segmento do cliente
    cliente.total_pedidos += 1
    cliente.total_gasto += total
    cliente.ultimo_pedido = datetime.now(timezone.utc)
    cliente.segmento = cliente_service.calcular_segmento_rfm(cliente)
    db.commit()

    return {"pedido": pedido_completo}


def obter_pedido(pedido_id: int, db: Session) -> Pedido:
    return _obter_pedido_completo(pedido_id, db)


def listar_pedidos_cliente(
    cliente_id: int,
    db: Session,
    limite: int = 20,
    offset: int = 0,
) -> list[Pedido]:
    return (
        db.query(Pedido)
        .filter(Pedido.cliente_id == cliente_id)
        .options(
            joinedload(Pedido.cliente),
            joinedload(Pedido.itens).joinedload(PedidoItem.modificadores),
        )
        .order_by(Pedido.criado_em.desc())
        .offset(offset)
        .limit(min(limite, 50))
        .all()
    )


def listar_pedidos(
    db: Session,
    status: str | None = None,
    tipo: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> list[Pedido]:
    q = db.query(Pedido).options(joinedload(Pedido.cliente)).order_by(Pedido.criado_em.desc())
    if status:
        q = q.filter(Pedido.status == status)
    if tipo:
        q = q.filter(Pedido.tipo == tipo)
    if data_inicio:
        q = q.filter(Pedido.criado_em >= datetime.combine(data_inicio, time.min))
    if data_fim:
        q = q.filter(Pedido.criado_em < datetime.combine(data_fim + timedelta(days=1), time.min))
    return q.offset((page - 1) * page_size).limit(page_size).all()


def contar_pedidos(
    db: Session,
    status: str | None = None,
    tipo: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> int:
    q = db.query(func.count(Pedido.id))
    if status:
        q = q.filter(Pedido.status == status)
    if tipo:
        q = q.filter(Pedido.tipo == tipo)
    if data_inicio:
        q = q.filter(Pedido.criado_em >= datetime.combine(data_inicio, time.min))
    if data_fim:
        q = q.filter(Pedido.criado_em < datetime.combine(data_fim + timedelta(days=1), time.min))
    return q.scalar() or 0


def deletar_pedido(pedido_id: int, db: Session) -> None:
    pedido = db.get(Pedido, pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    db.delete(pedido)
    db.commit()


def deletar_pedidos_periodo(periodo: str, db: Session) -> int:
    """Remove pedidos de um período. periodo: 'hoje' | 'semana'.
    Retorna a quantidade deletada.
    Usa data UTC para alinhar com os datetimes armazenados em UTC."""
    hoje = datetime.now(timezone.utc).date()
    if periodo == "hoje":
        data_inicio = hoje
        data_fim = hoje
    elif periodo == "semana":
        data_inicio = hoje - timedelta(days=hoje.weekday())  # segunda-feira
        data_fim = hoje
    else:
        raise HTTPException(status_code=400, detail="Período inválido. Use 'hoje' ou 'semana'.")

    pedidos = (
        db.query(Pedido)
        .filter(Pedido.criado_em >= datetime.combine(data_inicio, time.min))
        .filter(Pedido.criado_em < datetime.combine(data_fim + timedelta(days=1), time.min))
        .all()
    )
    total = len(pedidos)
    for p in pedidos:
        db.delete(p)
    db.commit()
    return total


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