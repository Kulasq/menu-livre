from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.cardapio import CardapioPublicoResponse
from app.schemas.configuracao import ConfiguracaoPublicaResponse
from app.services import cardapio_service
from app.services.configuracao_service import (
    obter_configuracoes,
    verificar_loja_aberta,
    horarios_para_schema,
)

router = APIRouter(prefix="/api", tags=["cardapio-publico"])


@router.get("/cardapio", response_model=CardapioPublicoResponse)
def obter_cardapio(db: Session = Depends(get_db)):
    return cardapio_service.obter_cardapio_publico(db)


@router.get("/configuracao", response_model=ConfiguracaoPublicaResponse)
def obter_configuracao_publica(db: Session = Depends(get_db)):
    config = obter_configuracoes(db)
    return ConfiguracaoPublicaResponse(
        nome_loja=config.nome_loja,
        logo_url=config.logo_url,
        banner_url=config.banner_url,
        whatsapp=config.whatsapp,
        chave_pix=config.chave_pix,
        taxa_entrega=config.taxa_entrega,
        pedido_minimo=config.pedido_minimo,
        tempo_entrega_min=config.tempo_entrega_min,
        tempo_entrega_max=config.tempo_entrega_max,
        aceitar_agendamentos=config.aceitar_agendamentos,
        mensagem_fechado=config.mensagem_fechado,
        instagram_url=config.instagram_url,
        horarios=horarios_para_schema(config),
        aberto=verificar_loja_aberta(config),
        fechado_manualmente=config.fechado_manualmente,
        cor_primaria=config.cor_primaria,
        cor_secundaria=config.cor_secundaria,
        cor_fundo=config.cor_fundo,
        cor_fonte=config.cor_fonte,
        cor_banner=config.cor_banner,
    )
