from __future__ import annotations
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from app.services.auth_service import hash_senha, verificar_senha


def obter_me(usuario: Usuario) -> Usuario:
    """Retorna o usuário autenticado. O model já está carregado pelo dep."""
    return usuario


def atualizar_me(usuario: Usuario, nome: str, email: str, db: Session) -> Usuario:
    """
    Atualiza nome e e-mail do usuário autenticado.
    Garante unicidade de e-mail antes de salvar.
    """
    email = email.strip().lower()

    # Unicidade: verifica se outro usuário já usa este e-mail
    conflito = (
        db.query(Usuario)
        .filter(Usuario.email == email, Usuario.id != usuario.id)
        .first()
    )
    if conflito:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está em uso por outra conta",
        )

    usuario.nome = nome.strip()
    usuario.email = email
    db.commit()
    db.refresh(usuario)
    return usuario


def alterar_senha(
    usuario: Usuario,
    senha_atual: str,
    senha_nova: str,
    db: Session,
) -> None:
    """
    Altera a senha do usuário autenticado.
    Exige confirmação da senha atual.
    A nova senha não pode ser igual à atual.
    """
    if not verificar_senha(senha_atual, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta",
        )

    if verificar_senha(senha_nova, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova senha deve ser diferente da senha atual",
        )

    usuario.senha_hash = hash_senha(senha_nova)
    db.commit()
