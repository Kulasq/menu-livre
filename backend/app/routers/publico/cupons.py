from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.schemas.cupom import CupomValidarRequest, CupomValidacaoResponse
from app.services import cupom_service

router = APIRouter(prefix="/api", tags=["cupons-publico"])


@router.post("/cupons/validar", response_model=CupomValidacaoResponse)
@limiter.limit("15/minute")
def validar_cupom(
    request: Request,
    dados: CupomValidarRequest = Body(...),
    db: Session = Depends(get_db),
):
    """Preview de validação de cupom para o checkout.
    Não aplica o cupom — apenas retorna o desconto calculado.
    Rate limited: 15 tentativas/min por IP para evitar brute force."""
    return cupom_service.validar_cupom(
        codigo=dados.codigo,
        subtotal=dados.subtotal,
        telefone=dados.telefone,
        db=db,
    )
