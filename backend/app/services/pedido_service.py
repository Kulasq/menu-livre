from __future__ import annotations
from datetime import date, timedelta
from sqlalchemy import func, delete
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from app.models.pedido import Pedido, PedidoItem, PedidoItemModificador
from app.models.produto import Produto
from app.models.cliente import Cliente
from app.models.modificador import Modificador
from app.models.configuracao import Configuracao
from app.models.cupom import Cupom
from app.schemas.pedido import PedidoCreate, PedidoAdminCreate, PedidoStatusUpdate, PedidoPagamentoUpdate
from app.services.whatsapp_service import formatar_mensagem, gerar_url
from app.services.configuracao_service import verificar_loja_aberta, calcular_proxima_abertura
from app.services import cliente_service
from app.services import estoque_service
from app.services import cupom_service
from app.tempo import agora_utc, hoje_brt, inicio_dia_utc

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


def _resolver_cliente_admin(dados: PedidoAdminCreate, db: Session) -> Cliente:
    """Resolve o cliente de um pedido do PDV: por id, por telefone (cria se novo),
    só por nome (cadastro rápido) ou o cliente sistema 'Balcão' quando anônimo."""
    _BALCAO_TELEFONE = "00000000000"

    if dados.cliente_id:
        cliente = db.get(Cliente, dados.cliente_id)
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        return cliente

    if dados.cliente_telefone:
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
        return cliente

    if dados.cliente_nome:
        # Cliente só com nome, sem telefone — cadastro rápido do PDV
        cliente = Cliente(nome=dados.cliente_nome, telefone=None)
        db.add(cliente)
        db.flush()
        return cliente

    # Sem identificação — usa/cria o cliente sistema "Balcão"
    cliente = db.query(Cliente).filter(
        Cliente.telefone == _BALCAO_TELEFONE
    ).first()
    if not cliente:
        cliente = Cliente(nome="Balcão", telefone=_BALCAO_TELEFONE)
        db.add(cliente)
        db.flush()
    return cliente


def _criar_pedido_core(
    dados: PedidoCreate | PedidoAdminCreate,
    cliente: Cliente,
    db: Session,
    *,
    aplicar_regras_loja: bool,
    nome_cliente_balcao: str | None = None,
) -> int:
    """Núcleo compartilhado de criação de pedido (público e admin/PDV).

    Faz a parte idêntica dos dois fluxos: validação de itens e modificadores,
    cupom, cálculo do total, abate de estoque e a transação única (pedido +
    estoque + uso de cupom + stats do cliente). Retorna o id do pedido criado.

    `cliente` já vem resolvido pelo chamador. `aplicar_regras_loja` liga as
    regras da vitrine pública (horário/agendamento e pedido mínimo) — o PDV
    passa False para criar a qualquer hora e sem piso de valor. Os efeitos
    pós-commit (SSE, WhatsApp, PIX, salvar endereço) ficam a cargo do chamador,
    pois divergem entre público e admin.
    """
    if dados.tipo == "delivery" and not dados.endereco_entrega:
        raise HTTPException(
            status_code=400,
            detail="Endereço de entrega obrigatório para delivery",
        )

    config = db.get(Configuracao, 1)
    taxa_entrega = config.taxa_entrega if config and dados.tipo == "delivery" else 0.0

    # ── Regras da vitrine (só público): status da loja + agendamento ─────────
    # PedidoAdminCreate não tem `agendado_para`; getattr mantém None para o PDV.
    agendado_para = getattr(dados, "agendado_para", None)

    if aplicar_regras_loja and config and not verificar_loja_aberta(config):
        # Fechada manualmente ou por horário sem aceitar agendamentos → bloqueia
        if config.fechado_manualmente or not config.aceitar_agendamentos:
            raise HTTPException(
                status_code=400,
                detail=config.mensagem_fechado or "A loja está fechada no momento.",
            )

        # Fechada por horário, mas aceita agendamentos — checar limite
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

    if (aplicar_regras_loja and config and config.pedido_minimo > 0
            and subtotal < config.pedido_minimo):
        raise HTTPException(
            status_code=400,
            detail=f"Pedido mínimo é R$ {config.pedido_minimo:.2f}",
        )

    # ── Cupom de desconto ────────────────────────────────────────────────────
    desconto_cupom = 0.0
    cupom_codigo_snapshot: str | None = None
    cupom_id_aplicado: int | None = None

    if dados.cupom_codigo:
        codigo_normalizado = dados.cupom_codigo.strip().upper()
        desconto_cupom, frete_gratis_cupom, produto_brinde_id = cupom_service.aplicar_cupom_no_pedido(
            codigo=codigo_normalizado,
            subtotal=subtotal,
            telefone=cliente.telefone,
            db=db,
        )
        if frete_gratis_cupom:
            taxa_entrega = 0.0
        cupom_codigo_snapshot = codigo_normalizado
        # Buscar id do cupom para registrar uso depois
        cupom_obj = db.query(Cupom).filter_by(codigo=codigo_normalizado).first()
        if cupom_obj:
            cupom_id_aplicado = cupom_obj.id
        # Adicionar brinde como item do pedido (preço zero, sem afetar subtotal)
        if produto_brinde_id:
            produto_brinde = (
                db.query(Produto)
                .filter(Produto.id == produto_brinde_id)
                .with_for_update()
                .populate_existing()
                .first()
            )
            if produto_brinde:
                # Abater estoque do brinde (não passa por abater_estoque_pedido
                # porque não tem PedidoItemCreate correspondente)
                if produto_brinde.controle_estoque:
                    if produto_brinde.estoque_atual < 1:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Brinde '{produto_brinde.nome}' sem estoque disponível",
                        )
                    produto_brinde.estoque_atual -= 1
                itens_db.append(PedidoItem(
                    produto_id=produto_brinde.id,
                    variante_id=None,
                    nome_snapshot=f"{produto_brinde.nome} ({codigo_normalizado})",
                    preco_snapshot=0.0,
                    quantidade=1,
                    subtotal=0.0,
                ))

    total = max(0.0, subtotal - desconto_cupom) + taxa_entrega
    numero = _numero_pedido(db)

    if dados.metodo_pagamento == "dinheiro" and dados.troco_para is not None:
        if dados.troco_para < total:
            raise HTTPException(
                status_code=400,
                detail=f"Troco inválido: valor deve ser maior ou igual ao total (R$ {total:.2f})",
            )

    # ── Abater estoque (produto + modificadores) antes de commitar ───────────
    # Passa itens_data (schemas) para obter produto_id, quantidade e modificadores.
    # itens_db ainda não tem IDs; o abate opera direto nos objetos ORM consultados.
    estoque_service.abater_estoque_pedido(dados.itens, itens_db, db)

    pedido = Pedido(
        numero=numero,
        cliente_id=cliente.id,
        tipo=dados.tipo,
        status="pendente",
        endereco_entrega=dados.endereco_entrega,
        subtotal=subtotal,
        taxa_entrega=taxa_entrega,
        desconto_cupom=desconto_cupom,
        cupom_codigo=cupom_codigo_snapshot,
        cupom_id=cupom_id_aplicado,
        total=total,
        metodo_pagamento=dados.metodo_pagamento,
        troco_para=dados.troco_para,
        status_pagamento="pendente",
        observacao=dados.observacao,
        nome_cliente_balcao=nome_cliente_balcao,
        agendado_para=agendado_para,
        itens=itens_db,
    )
    db.add(pedido)

    # ── Transação única: pedido + estoque + uso de cupom + stats do cliente ──
    # Tudo foi construído na sessão (abate de estoque, incremento de cupom).
    # Um único commit garante atomicidade: qualquer falha desfaz o pedido
    # inteiro via rollback — nada de pedido órfão ou cupom incrementado sem
    # pedido. O flush obtém o pedido.id sem fechar a transação.
    try:
        db.flush()
        pedido_id = pedido.id

        # Auditoria de uso do cupom (mesma transação)
        if cupom_id_aplicado:
            cupom_service.registrar_uso_cupom(
                cupom_id=cupom_id_aplicado,
                pedido_id=pedido_id,
                telefone=cliente.telefone,
                desconto_aplicado=desconto_cupom,
                subtotal_pedido=subtotal,
                db=db,
            )

        # Stats e segmento do cliente (mesma transação)
        cliente.total_pedidos += 1
        cliente.total_gasto += total
        cliente.ultimo_pedido = agora_utc()
        cliente.segmento = cliente_service.calcular_segmento_rfm(cliente)

        db.commit()
    except Exception:
        db.rollback()
        raise

    return pedido_id


def criar_pedido(dados: PedidoCreate, cliente_id: int, db: Session) -> dict:
    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    pedido_id = _criar_pedido_core(dados, cliente, db, aplicar_regras_loja=True)

    # ── Efeitos colaterais pós-commit (falha NÃO derruba o pedido) ───────────
    # Recarregar com todos os relacionamentos para a resposta/mensagem WhatsApp
    pedido_completo = _obter_pedido_completo(pedido_id, db)

    # Notifica admins conectados via SSE — falha silenciosa
    try:
        from app.services import pedido_pubsub
        pedido_pubsub.notify({
            "id":        pedido_completo.id,
            "numero":    pedido_completo.numero,
            "total":     float(pedido_completo.total),
            "tipo":      pedido_completo.tipo,
            "criado_em": pedido_completo.criado_em.isoformat() if pedido_completo.criado_em else None,
        })
    except Exception:
        pass

    # Auto-salvar endereço de delivery — falha silenciosa (commita por conta própria)
    if dados.tipo == "delivery" and dados.endereco_entrega:
        try:
            cliente_service.salvar_endereco_se_novo(db, cliente_id, dados.endereco_entrega)
        except Exception:
            pass

    config = db.get(Configuracao, 1)
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
        cobranca = gerar_cobranca_pix(chave_pix, pedido_completo.total, nome_loja, tipo_chave=tipo_chave)
        if cobranca:
            resultado["pix_br_code"] = cobranca["br_code"]
            resultado["pix_qr_code_base64"] = cobranca["qr_code_base64"]

    return resultado


def criar_pedido_admin(dados: PedidoAdminCreate, db: Session) -> dict:
    """Cria pedido pelo admin (PDV). Resolve/cria o cliente, bypassa as regras de
    horário/agendamento e pedido mínimo da vitrine, não gera URL WhatsApp e NÃO
    dispara o alarme SSE (quem criou foi o próprio admin — notificá-lo é ruído).
    """
    cliente = _resolver_cliente_admin(dados, db)
    nome_balcao = dados.nome_cliente_balcao if dados.tipo == "balcao" else None

    pedido_id = _criar_pedido_core(
        dados, cliente, db,
        aplicar_regras_loja=False,
        nome_cliente_balcao=nome_balcao,
    )

    return {"pedido": _obter_pedido_completo(pedido_id, db)}


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
    # criado_em é armazenado em UTC. O frontend envia datas no fuso local (BRT);
    # inicio_dia_utc() alinha os limites ao dia civil brasileiro (ver app/tempo.py).
    q = db.query(Pedido).options(joinedload(Pedido.cliente)).order_by(Pedido.criado_em.desc())
    if status:
        q = q.filter(Pedido.status == status)
    if tipo:
        q = q.filter(Pedido.tipo == tipo)
    if data_inicio:
        q = q.filter(Pedido.criado_em >= inicio_dia_utc(data_inicio))
    if data_fim:
        q = q.filter(Pedido.criado_em < inicio_dia_utc(data_fim + timedelta(days=1)))
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
        q = q.filter(Pedido.criado_em >= inicio_dia_utc(data_inicio))
    if data_fim:
        q = q.filter(Pedido.criado_em < inicio_dia_utc(data_fim + timedelta(days=1)))
    return q.scalar() or 0


def deletar_pedido(pedido_id: int, db: Session) -> None:
    # Carregar com itens para restauro de estoque
    pedido = _obter_pedido_completo(pedido_id, db)

    # Restaurar estoque se pedido não foi entregue
    if pedido.status != "entregue":
        estoque_service.restaurar_estoque_pedido(pedido, db)

    db.delete(pedido)
    db.commit()


def deletar_pedidos_periodo(periodo: str, db: Session) -> int:
    """Remove pedidos de um período. periodo: 'hoje' | 'semana'.
    Retorna a quantidade deletada.
    Usa data BRT (UTC-3) para alinhar com o dia local do operador."""
    hoje = hoje_brt()
    if periodo == "hoje":
        data_inicio = hoje
        data_fim = hoje
    elif periodo == "semana":
        data_inicio = hoje - timedelta(days=hoje.weekday())  # segunda-feira
        data_fim = hoje
    else:
        raise HTTPException(status_code=400, detail="Período inválido. Use 'hoje' ou 'semana'.")

    # Delete em lote (uma instrução SQL) em vez de carregar tudo + loop de db.delete.
    # Os filhos (pedido_itens → pedido_item_modificadores, cupom_usos) caem por
    # ON DELETE CASCADE do FK — o PRAGMA foreign_keys=ON está ativo (database.py).
    resultado = db.execute(
        delete(Pedido)
        .where(Pedido.criado_em >= inicio_dia_utc(data_inicio))
        .where(Pedido.criado_em < inicio_dia_utc(data_fim + timedelta(days=1)))
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return resultado.rowcount


def atualizar_status(pedido_id: int, dados: PedidoStatusUpdate, db: Session) -> Pedido:
    pedido = _obter_pedido_completo(pedido_id, db)
    if dados.status not in _TRANSICOES.get(pedido.status, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Transição inválida: {pedido.status} → {dados.status}",
        )

    # Restaurar estoque ao cancelar — antes do commit
    if dados.status == "cancelado" and pedido.status != "entregue":
        estoque_service.restaurar_estoque_pedido(pedido, db)

    pedido.status = dados.status
    pedido.atualizado_em = agora_utc()
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