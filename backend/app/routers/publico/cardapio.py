from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.cardapio import CardapioPublicoResponse
from app.services import cardapio_service

router = APIRouter(prefix="/api", tags=["cardapio-publico"])


@router.get("/cardapio", response_model=CardapioPublicoResponse)
def obter_cardapio(db: Session = Depends(get_db)):
    return cardapio_service.obter_cardapio_publico(db)