from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.cupom import Cupom, CupomUso
from app.models.cliente import Cliente
from app.models.pedido import Pedido
from app.schemas.cupom import CupomCreate, CupomUpdate, CupomValidarRequest, CupomValidacaoResponse


# ── CRUD admin ────────────────────────────────────────────────────────────────

def listar_cupons(db: Session) -> list[dict]:
    """Lista cupons com agregados: faturamento_gerado e ultimo_uso."""
    cupons = db.query(Cupom).order_by(Cupom.criado_em.desc()).all()
    resultado = []
    for cupom in cupons:
        agg = (
            db.query(
                func.sum(CupomUso.subtotal_pedido).label("faturamento"),
                func.max(CupomUso.criado_em).label("ultimo_uso"),
            )
            .filter(CupomUso.cupom_id == cupom.id)
            .first()
        )
        resultado.append({
            "id": cupom.id,
            "codigo": cupom.codigo,
            "tipo": cupom.tipo,
            "valor": cupom.valor,
            "desconto_maximo": cupom.desconto_maximo,
            "produto_brinde_id": cupom.produto_brinde_id,
            "produto_brinde": cupom.produto_brinde,
            "valor_minimo_pedido": cupom.valor_minimo_pedido,
            "limite_total_usos": cupom.limite_total_usos,
            "usos_atuais": cupom.usos_atuais,
            "limite_por_cliente": cupom.limite_por_cliente,
            "somente_primeira_compra": cupom.somente_primeira_compra,
            "data_inicio": cupom.data_inicio,
            "data_fim": cupom.data_fim,
            "ativo": cupom.ativo,
            "criado_em": cupom.criado_em,
            "atualizado_em": cupom.atualizado_em,
            "faturamento_gerado": float(agg.faturamento or 0),
            "ultimo_uso": agg.ultimo_uso,
        })
    return resultado


def obter_cupom(cupom_id: int, db: Session) -> Cupom:
    cupom = db.get(Cupom, cupom_id)
    if not cupom:
        raise HTTPException(status_code=404, detail="Cupom não encontrado")
    return cupom


def criar_cupom(dados: CupomCreate, db: Session) -> Cupom:
    existente = db.query(Cupom).filter(Cupom.codigo == dados.codigo).first()
    if existente:
        raise HTTPException(status_code=409, detail="Já existe um cupom com esse código")

    cupom = Cupom(
        codigo=dados.codigo,
        tipo=dados.tipo,
        valor=dados.valor,
        desconto_maximo=dados.desconto_maximo,
        produto_brinde_id=dados.produto_brinde_id,
        valor_minimo_pedido=dados.valor_minimo_pedido,
        limite_total_usos=dados.limite_total_usos,
        limite_por_cliente=dados.limite_por_cliente,
        somente_primeira_compra=dados.somente_primeira_compra,
        data_inicio=dados.data_inicio,
        data_fim=dados.data_fim,
        ativo=dados.ativo,
    )
    db.add(cupom)
    db.commit()
    db.refresh(cupom)
    return cupom


def atualizar_cupom(cupom_id: int, dados: CupomUpdate, db: Session) -> Cupom:
    cupom = obter_cupom(cupom_id, db)

    if dados.codigo is not None and dados.codigo != cupom.codigo:
        existente = db.query(Cupom).filter(Cupom.codigo == dados.codigo).first()
        if existente:
            raise HTTPException(status_code=409, detail="Já existe um cupom com esse código")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(cupom, campo, valor)

    db.commit()
    db.refresh(cupom)
    return cupom


def deletar_cupom(cupom_id: int, db: Session) -> None:
    cupom = obter_cupom(cupom_id, db)
    db.delete(cupom)
    db.commit()


def listar_usos_cupom(cupom_id: int, db: Session) -> list[CupomUso]:
    obter_cupom(cupom_id, db)
    return (
        db.query(CupomUso)
        .filter(CupomUso.cupom_id == cupom_id)
        .order_by(CupomUso.criado_em.desc())
        .all()
    )


# ── Validação de cupom ────────────────────────────────────────────────────────

def validar_cupom(
    codigo: str,
    subtotal: float,
    telefone: str | None,
    db: Session,
) -> CupomValidacaoResponse:
    """Preview de validação — NÃO incrementa contadores.
    Retorna desconto calculado para exibição no checkout.
    A aplicação real ocorre dentro da transação de criar_pedido."""

    # Normalizar antes da query (case-insensitive de ponta a ponta)
    codigo = codigo.strip().upper()
    # Mensagem genérica para não vazar existência do código
    _INVALIDO = "Cupom inválido ou expirado"

    cupom = db.query(Cupom).filter(Cupom.codigo == codigo).first()

    if not cupom or not cupom.ativo:
        return CupomValidacaoResponse(valido=False, motivo=_INVALIDO)

    agora = datetime.now(timezone.utc)

    if cupom.data_inicio:
        inicio = cupom.data_inicio
        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=timezone.utc)
        if agora < inicio:
            return CupomValidacaoResponse(valido=False, motivo=_INVALIDO)

    if cupom.data_fim:
        fim = cupom.data_fim
        if fim.tzinfo is None:
            fim = fim.replace(tzinfo=timezone.utc)
        if agora > fim:
            return CupomValidacaoResponse(valido=False, motivo=_INVALIDO)

    if cupom.limite_total_usos is not None and cupom.usos_atuais >= cupom.limite_total_usos:
        return CupomValidacaoResponse(valido=False, motivo="Cupom esgotado")

    if subtotal < cupom.valor_minimo_pedido:
        return CupomValidacaoResponse(
            valido=False,
            motivo=f"Valor mínimo para esse cupom: R$ {cupom.valor_minimo_pedido:.2f}".replace(".", ","),
        )

    if telefone:
        if cupom.somente_primeira_compra:
            pedidos_anteriores = db.query(func.count(Pedido.id)).filter(
                Pedido.cupom_codigo.isnot(None),
                # Qualquer pedido do cliente (não só com cupom)
            ).scalar()
            # Verifica se cliente já fez algum pedido (qualquer um)
            pedido_anterior = db.query(Pedido).join(
                Cliente, Pedido.cliente_id == Cliente.id
            ).filter(Cliente.telefone == telefone).first()
            if pedido_anterior:
                return CupomValidacaoResponse(
                    valido=False, motivo="Cupom válido somente para a primeira compra"
                )

        if cupom.limite_por_cliente > 0:
            usos_cliente = db.query(func.count(CupomUso.id)).filter(
                CupomUso.cupom_id == cupom.id,
                CupomUso.cliente_telefone == telefone,
            ).scalar() or 0
            if usos_cliente >= cupom.limite_por_cliente:
                return CupomValidacaoResponse(valido=False, motivo="Cupom já utilizado")

    desconto, frete_gratis, brinde_id, brinde_nome = _calcular_desconto(cupom, subtotal, db)
    total_com_desconto = max(0.0, subtotal - desconto)

    return CupomValidacaoResponse(
        valido=True,
        desconto=desconto,
        frete_gratis=frete_gratis,
        produto_brinde_id=brinde_id,
        produto_brinde_nome=brinde_nome,
        total_com_desconto=total_com_desconto,
    )


def _calcular_desconto(
    cupom: Cupom, subtotal: float, db: Session
) -> tuple[float, bool, int | None, str | None]:
    """Retorna (desconto_R$, frete_gratis, produto_brinde_id, produto_brinde_nome)."""
    if cupom.tipo == "percentual":
        desconto = subtotal * (cupom.valor / 100)
        if cupom.desconto_maximo:
            desconto = min(desconto, cupom.desconto_maximo)
        return round(desconto, 2), False, None, None

    if cupom.tipo == "valor_fixo":
        desconto = min(cupom.valor, subtotal)  # não pode ser negativo
        return round(desconto, 2), False, None, None

    if cupom.tipo == "frete_gratis":
        return 0.0, True, None, None

    if cupom.tipo == "brinde":
        nome = None
        if cupom.produto_brinde_id and cupom.produto_brinde:
            nome = cupom.produto_brinde.nome
        return 0.0, False, cupom.produto_brinde_id, nome

    return 0.0, False, None, None


# ── Aplicação real (dentro da transação de criar_pedido) ─────────────────────

def aplicar_cupom_no_pedido(
    codigo: str,
    subtotal: float,
    telefone: str | None,
    db: Session,
) -> tuple[float, bool, int | None]:
    """Valida, incrementa contadores e retorna (desconto, frete_gratis, produto_brinde_id).
    Deve ser chamado ANTES do commit do pedido."""
    validacao = validar_cupom(codigo, subtotal, telefone, db)
    if not validacao.valido:
        raise HTTPException(status_code=400, detail=validacao.motivo or "Cupom inválido")

    # Lock da linha do cupom: serializa o incremento e fecha a janela de race
    # entre dois pedidos que aplicam o mesmo cupom ao mesmo tempo. populate_existing
    # garante que usos_atuais reflita o valor atual no banco (não o cacheado da
    # validação). Em SQLite, with_for_update serializa via lock de escrita do WAL.
    cupom = (
        db.query(Cupom)
        .filter(Cupom.codigo == codigo)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if cupom is None:
        raise HTTPException(status_code=400, detail="Cupom inválido ou expirado")

    # Re-checar o limite DENTRO do lock antes de incrementar
    if cupom.limite_total_usos is not None and cupom.usos_atuais >= cupom.limite_total_usos:
        raise HTTPException(status_code=400, detail="Cupom esgotado")

    cupom.usos_atuais += 1

    return validacao.desconto, validacao.frete_gratis, validacao.produto_brinde_id


def registrar_uso_cupom(
    cupom_id: int,
    pedido_id: int,
    telefone: str | None,
    desconto_aplicado: float,
    subtotal_pedido: float,
    db: Session,
) -> None:
    """Cria registro de auditoria em CupomUso. Chamado após commit do pedido."""
    uso = CupomUso(
        cupom_id=cupom_id,
        pedido_id=pedido_id,
        cliente_telefone=telefone,
        desconto_aplicado=desconto_aplicado,
        subtotal_pedido=subtotal_pedido,
    )
    db.add(uso)
    # Não faz commit — quem chama é responsável pelo commit
