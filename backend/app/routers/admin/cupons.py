from __future__ import annotations
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.schemas.cupom import (
    CupomCreate, CupomUpdate, CupomResponse, CupomUsoResponse,
)
from app.services import cupom_service

router = APIRouter(prefix="/api/admin", tags=["admin-cupons"])


@router.get("/cupons", response_model=list[CupomResponse])
def listar_cupons(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cupom_service.listar_cupons(db)


@router.post("/cupons", response_model=CupomResponse, status_code=201)
def criar_cupom(
    dados: CupomCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cupom_service.criar_cupom(dados, db)


@router.put("/cupons/{cupom_id}", response_model=CupomResponse)
def atualizar_cupom(
    cupom_id: int,
    dados: CupomUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cupom_service.atualizar_cupom(cupom_id, dados, db)


@router.delete("/cupons/{cupom_id}", status_code=204)
def deletar_cupom(
    cupom_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    cupom_service.deletar_cupom(cupom_id, db)


@router.get("/cupons/{cupom_id}/usos", response_model=list[CupomUsoResponse])
def listar_usos_cupom(
    cupom_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return cupom_service.listar_usos_cupom(cupom_id, db)
