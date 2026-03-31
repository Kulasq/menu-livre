from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.services import dashboard_service

router = APIRouter(prefix="/api/admin/dashboard", tags=["admin-dashboard"])


@router.get("/resumo")
def obter_resumo(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return dashboard_service.obter_resumo(db)