from __future__ import annotations
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.config import settings
from app.models.usuario import Usuario

pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12, deprecated="auto")

# Refresh tokens invalidados por logout ficam aqui.
# Funciona bem para single-process (SQLite + 1 worker).
_tokens_invalidados: set[str] = set()


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    return pwd_context.verify(senha, hash)


def criar_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": str(user_id), "type": "access", "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def criar_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    return jwt.encode(
        {"sub": str(user_id), "type": "refresh", "exp": expire},
        settings.REFRESH_SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def criar_token_cliente(cliente_id: int) -> str:
    """Token de sessão para clientes do cardápio público (24h)."""
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    return jwt.encode(
        {"sub": str(cliente_id), "type": "cliente", "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def login_admin(email: str, senha: str, db: Session) -> dict:
    usuario = db.query(Usuario).filter(Usuario.email == email).first()

    if not usuario or not verificar_senha(senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
        )

    if not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada",
        )

    usuario.ultimo_acesso = datetime.now(timezone.utc)
    db.commit()

    return {
        "access_token": criar_access_token(usuario.id),
        "refresh_token": criar_refresh_token(usuario.id),
        "token_type": "bearer",
        "usuario_nome": usuario.nome,
        "usuario_role": usuario.role,
    }


def renovar_access_token(refresh_token: str, db: Session) -> dict:
    if refresh_token in _tokens_invalidados:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )

    try:
        payload = jwt.decode(
            refresh_token,
            settings.REFRESH_SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("type") != "refresh":
            raise ValueError()
        user_id = int(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado",
        )

    usuario = db.get(Usuario, user_id)
    if not usuario or not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
        )

    return {
        "access_token": criar_access_token(usuario.id),
        "token_type": "bearer",
    }


def logout_admin(refresh_token: str) -> None:
    _tokens_invalidados.add(refresh_token)