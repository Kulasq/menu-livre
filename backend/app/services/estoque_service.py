"""Serviço dedicado de controle de estoque.

Concentra toda a lógica de abate, restauro e ajuste manual de estoque
para Produto e Modificador. Pedido service delega aqui — nunca duplicar
essa lógica em outro lugar.

Decisões de design:
- Abate acontece na criação do pedido (status=pendente), não no confirmado.
  Protege contra oversell: dois clientes não podem comprar o mesmo último item.
- disponivel (Produto/Modificador) NÃO é tocado automaticamente aqui.
  A disponibilidade efetiva é calculada na leitura (cardapio_service), nunca
  gravada como efeito colateral de estoque. Isso evita o bug de "produto
  continua oculto mesmo após reposição".
- Re-check pós-decremento: após somar -qty, se estoque_atual < 0 o DB ainda
  não commitou — levantamos 400 e o caller faz rollback. Proteção mínima
  contra TOCTOU em volume de MVP.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.modificador import Modificador
from app.models.pedido import Pedido, PedidoItem
from app.models.produto import Produto
from app.schemas.cardapio import EstoqueAjusteRequest


# ── helpers de disponibilidade efetiva ───────────────────────────────────────

def produto_disponivel_efetivo(produto: Produto) -> bool:
    """Produto está disponível para o cliente se:
    1. disponivel=True (flag manual do admin)
    2. E, se controle_estoque ligado, estoque_atual > 0
    3. E, se tem grupo obrigatório, ao menos uma opção disponível em cada grupo.
    O critério 3 é verificado separadamente em obter_cardapio_publico porque
    requer acesso às opções carregadas.
    """
    if not produto.disponivel:
        return False
    if produto.controle_estoque and produto.estoque_atual <= 0:
        return False
    return True


def modificador_disponivel_efetivo(mod: Modificador) -> bool:
    """Opção de modificador está disponível se:
    1. disponivel=True
    2. E, se controle_estoque ligado, estoque_atual > 0
    """
    if not mod.disponivel:
        return False
    if mod.controle_estoque and mod.estoque_atual <= 0:
        return False
    return True


# ── abate de estoque ao criar pedido ─────────────────────────────────────────

def abater_estoque_pedido(itens_data: list, itens_orm: list[PedidoItem], db: Session) -> None:
    """Abate estoque de produtos e modificadores para os itens do pedido.

    Parâmetros:
        itens_data: lista de PedidoItemCreate (schemas, com produto_id,
                    quantidade e lista de modificadores selecionados)
        itens_orm:  instâncias PedidoItem já construídas (para pegar IDs)
        db:         sessão SQLAlchemy — NÃO commita aqui; o caller commita.

    Levanta HTTPException 400 se:
    - produto com controle_estoque=True e estoque_atual < quantidade
    - modificador com controle_estoque=True e estoque_atual < quantidade

    Re-check pós-decremento: se após subtrair o valor ficar negativo,
    levanta 400 e sinaliza para rollback (sem commit feito).
    """
    for item_data in itens_data:
        if not item_data.produto_id:
            continue

        # Lock da linha do produto: fecha o TOCTOU entre validar e decrementar.
        # populate_existing refresca estoque_atual com o valor atual do banco
        # (mesmo que o objeto já esteja na sessão por leituras anteriores).
        # Em SQLite, with_for_update serializa via lock de escrita do WAL.
        produto = (
            db.query(Produto)
            .filter(Produto.id == item_data.produto_id)
            .with_for_update()
            .populate_existing()
            .first()
        )
        if not produto:
            continue

        qty = item_data.quantidade

        # ── abate do produto ──────────────────────────────────────────────
        if produto.controle_estoque:
            if produto.estoque_atual < qty:
                raise HTTPException(
                    status_code=400,
                    detail=f"Estoque insuficiente para '{produto.nome}' "
                           f"(disponível: {produto.estoque_atual})",
                )
            produto.estoque_atual -= qty
            # re-check pós-decremento (guarda contra race condition)
            if produto.estoque_atual < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Estoque insuficiente para '{produto.nome}'",
                )

        # ── abate dos modificadores selecionados ──────────────────────────
        for mod_data in item_data.modificadores:
            if not mod_data.modificador_id:
                continue
            # Mesmo lock por linha do modificador (ver comentário do produto acima)
            mod = (
                db.query(Modificador)
                .filter(Modificador.id == mod_data.modificador_id)
                .with_for_update()
                .populate_existing()
                .first()
            )
            if not mod or not mod.controle_estoque:
                continue

            if mod.estoque_atual < qty:
                raise HTTPException(
                    status_code=400,
                    detail=f"Estoque insuficiente para a opção '{mod.nome}' "
                           f"(disponível: {mod.estoque_atual})",
                )
            mod.estoque_atual -= qty
            if mod.estoque_atual < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Estoque insuficiente para a opção '{mod.nome}'",
                )


# ── restauro de estoque ao cancelar/excluir pedido ────────────────────────────

def restaurar_estoque_pedido(pedido: Pedido, db: Session) -> None:
    """Restaura estoque de produtos e modificadores de um pedido cancelado/excluído.

    Deve ser chamado ANTES do commit de cancelamento/exclusão.
    Só restaura se o produto/modificador ainda existe no banco (SET NULL preserva
    histórico mas torna produto_id/modificador_id nullable).
    NÃO restaura se pedido.status == 'entregue' — o caller garante isso.
    """
    for item in pedido.itens:
        qty = item.quantidade

        # ── restauro do produto ───────────────────────────────────────────
        if item.produto_id:
            produto = db.get(Produto, item.produto_id)
            if produto and produto.controle_estoque:
                produto.estoque_atual += qty

        # ── restauro dos modificadores ────────────────────────────────────
        for mod_item in item.modificadores:
            if mod_item.modificador_id:
                mod = db.get(Modificador, mod_item.modificador_id)
                if mod and mod.controle_estoque:
                    mod.estoque_atual += qty


# ── ajuste manual de estoque (admin) ─────────────────────────────────────────

def ajustar_estoque_produto(produto_id: int, dados: EstoqueAjusteRequest, db: Session) -> Produto:
    """Ajusta estoque de um produto via painel admin.

    Operações:
    - definir:     define estoque_atual = dados.valor (>= 0)
    - incrementar: estoque_atual += dados.valor
    - decrementar: estoque_atual -= dados.valor (não vai abaixo de 0)
    - zerar:       estoque_atual = 0

    Levanta 404 se produto não encontrado.
    Levanta 400 se resultado seria negativo.
    """
    produto = db.get(Produto, produto_id)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    produto.estoque_atual = _calcular_novo_estoque(
        atual=produto.estoque_atual,
        operacao=dados.operacao,
        valor=dados.valor,
        nome=produto.nome,
    )
    db.commit()
    db.refresh(produto)
    return produto


def ajustar_estoque_modificador(opcao_id: int, dados: EstoqueAjusteRequest, db: Session) -> Modificador:
    """Ajusta estoque de uma opção de modificador via painel admin.

    Mesma lógica de ajustar_estoque_produto.
    Levanta 404 se opção não encontrada.
    """
    mod = db.get(Modificador, opcao_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Opção não encontrada")

    mod.estoque_atual = _calcular_novo_estoque(
        atual=mod.estoque_atual,
        operacao=dados.operacao,
        valor=dados.valor,
        nome=mod.nome,
    )
    db.commit()
    db.refresh(mod)
    return mod


def _calcular_novo_estoque(atual: int, operacao: str, valor: int, nome: str) -> int:
    """Calcula o novo valor de estoque e valida limites.

    Levanta HTTPException 400 se resultado seria negativo.
    Não persiste nada — só calcula.
    """
    match operacao:
        case "definir":
            novo = valor
        case "incrementar":
            novo = atual + valor
        case "decrementar":
            novo = atual - valor
        case "zerar":
            novo = 0
        case _:
            raise HTTPException(status_code=400, detail=f"Operação inválida: {operacao}")

    if novo < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Estoque de '{nome}' não pode ficar negativo "
                   f"(atual: {atual}, operação: {operacao} {valor})",
        )
    return novo
