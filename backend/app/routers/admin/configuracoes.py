from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.schemas.configuracao import ConfiguracaoUpdate, ConfiguracaoResponse
from app.services import configuracao_service
from app.services.configuracao_service import horarios_para_schema

router = APIRouter(prefix="/api/admin/configuracoes", tags=["admin-configuracoes"])


@router.get("", response_model=ConfiguracaoResponse)
def obter_configuracoes(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    config = configuracao_service.obter_configuracoes(db)
    config.horarios = horarios_para_schema(config)
    return config


@router.put("", response_model=ConfiguracaoResponse)
def atualizar_configuracoes(
    dados: ConfiguracaoUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    config = configuracao_service.atualizar_configuracoes(dados, db)
    config.horarios = horarios_para_schema(config)
    return config
