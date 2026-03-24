from __future__ import annotations
from sqlalchemy import String, Boolean, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class GrupoModificador(Base):
    __tablename__ = "grupos_modificadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    produto_id: Mapped[int | None] = mapped_column(
        ForeignKey("produtos.id", ondelete="CASCADE"), nullable=True, index=True
    )
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    obrigatorio: Mapped[bool] = mapped_column(Boolean, default=False)
    selecao_minima: Mapped[int] = mapped_column(Integer, default=0)
    selecao_maxima: Mapped[int] = mapped_column(Integer, default=1)
    ordem: Mapped[int] = mapped_column(Integer, default=0)

    modificadores: Mapped[list[Modificador]] = relationship(
        "Modificador", back_populates="grupo", cascade="all, delete-orphan"
    )


class Modificador(Base):
    __tablename__ = "modificadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    grupo_id: Mapped[int] = mapped_column(
        ForeignKey("grupos_modificadores.id", ondelete="CASCADE"), index=True
    )
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    preco_adicional: Mapped[float] = mapped_column(Float, default=0.0)
    disponivel: Mapped[bool] = mapped_column(Boolean, default=True)
    ordem: Mapped[int] = mapped_column(Integer, default=0)

    grupo: Mapped[GrupoModificador] = relationship("GrupoModificador", back_populates="modificadores")