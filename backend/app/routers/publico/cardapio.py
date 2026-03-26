from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.cardapio import CardapioPublicoResponse
from app.models.configuracao import Configuracao
from app.services import cardapio_service

router = APIRouter(prefix="/api", tags=["cardapio-publico"])


@router.get("/cardapio", response_model=CardapioPublicoResponse)
def obter_cardapio(db: Session = Depends(get_db)):
    return cardapio_service.obter_cardapio_publico(db)


@router.get("/configuracao")
def obter_configuracao(db: Session = Depends(get_db)):
    config = db.get(Configuracao, 1)
    if not config:
        return {}
    return {
        "nome_loja": config.nome_loja,
        "logo_url": config.logo_url,
        "banner_url": config.banner_url,
        "whatsapp": config.whatsapp,
        "chave_pix": config.chave_pix,
        "taxa_entrega": config.taxa_entrega,
        "pedido_minimo": config.pedido_minimo,
        "tempo_entrega_min": config.tempo_entrega_min,
        "tempo_entrega_max": config.tempo_entrega_max,
        "aceitar_pedidos": config.aceitar_pedidos,
        "mensagem_fechado": config.mensagem_fechado,
        "instagram_url": config.instagram_url,
    }