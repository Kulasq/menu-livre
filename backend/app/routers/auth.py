from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    AccessTokenResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(dados: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login_admin(dados.email, dados.senha, db)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(dados: RefreshRequest, db: Session = Depends(get_db)):
    return auth_service.renovar_access_token(dados.refresh_token, db)


@router.post("/logout", status_code=204)
def logout(dados: RefreshRequest):
    auth_service.logout_admin(dados.refresh_token)