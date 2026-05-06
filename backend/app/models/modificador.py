from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, Integer, Float, ForeignKey, Table, Column, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from app.models.produto import Produto


# Tabela de junção M:N produto ↔ grupo_modificador
produto_grupo_modificador = Table(
    "produto_grupo_modificador",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("produto_id", Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("grupo_id", Integer, ForeignKey("grupos_modificadores.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("ordem", Integer, nullable=False, default=0),
    UniqueConstraint("produto_id", "grupo_id", name="uq_produto_grupo"),
)


class GrupoModificador(Base):
    __tablename__ = "grupos_modificadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    obrigatorio: Mapped[bool] = mapped_column(Boolean, default=False)
    selecao_minima: Mapped[int] = mapped_column(Integer, default=0)
    selecao_maxima: Mapped[int] = mapped_column(Integer, default=1)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    produtos: Mapped[list["Produto"]] = relationship(
        "Produto",
        secondary=produto_grupo_modificador,
        back_populates="grupos_modificadores",
    )
    modificadores: Mapped[list["Modificador"]] = relationship(
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
    controle_estoque: Mapped[bool] = mapped_column(Boolean, default=False)
    estoque_atual: Mapped[int] = mapped_column(Integer, default=0)
    estoque_minimo: Mapped[int] = mapped_column(Integer, default=0)
    ordem: Mapped[int] = mapped_column(Integer, default=0)

    grupo: Mapped["GrupoModificador"] = relationship(
        "GrupoModificador", back_populates="modificadores"
    )
