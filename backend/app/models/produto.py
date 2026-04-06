from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.database import Base

if TYPE_CHECKING:
    from app.models.categoria import Categoria
    from app.models.modificador import GrupoModificador


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"), index=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    preco: Mapped[float] = mapped_column(Float, nullable=False)
    foto_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    disponivel: Mapped[bool] = mapped_column(Boolean, default=True)
    destaque: Mapped[bool] = mapped_column(Boolean, default=False)
    controle_estoque: Mapped[bool] = mapped_column(Boolean, default=False)
    estoque_atual: Mapped[int] = mapped_column(Integer, default=0)
    estoque_minimo: Mapped[int] = mapped_column(Integer, default=0)
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    categoria: Mapped["Categoria"] = relationship("Categoria", lazy="select")
    grupos_modificadores: Mapped[list["GrupoModificador"]] = relationship(
        "GrupoModificador",
        back_populates="produto",
        cascade="all, delete-orphan",
        lazy="select",
    )