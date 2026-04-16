from __future__ import annotations
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_admin
from app.models.usuario import Usuario
from app.schemas.auth import AlterarSenhaRequest, UsuarioMeResponse, UsuarioMeUpdate
from app.services import usuario_service

router = APIRouter(prefix="/api/auth", tags=["conta"])


@router.get("/me", response_model=UsuarioMeResponse)
def obter_me(usuario: Usuario = Depends(get_current_admin)):
    """Retorna os dados do usuário autenticado."""
    return usuario_service.obter_me(usuario)


@router.put("/me", response_model=UsuarioMeResponse)
def atualizar_me(
    dados: UsuarioMeUpdate,
    usuario: Usuario = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Atualiza nome e e-mail do usuário autenticado."""
    return usuario_service.atualizar_me(usuario, dados.nome, dados.email, db)


@router.put("/alterar-senha", status_code=status.HTTP_204_NO_CONTENT)
def alterar_senha(
    dados: AlterarSenhaRequest,
    usuario: Usuario = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Altera a senha do usuário autenticado. Exige senha atual para confirmação."""
    usuario_service.alterar_senha(usuario, dados.senha_atual, dados.senha_nova, db)
