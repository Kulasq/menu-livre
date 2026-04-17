from __future__ import annotations
from sqlalchemy import String, Boolean, DateTime, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    telefone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    endereco_padrao: Mapped[str | None] = mapped_column(Text, nullable=True)
    pontos: Mapped[int] = mapped_column(Integer, default=0)
    nivel_fidelidade: Mapped[str] = mapped_column(String(20), default="bronze")
    total_pedidos: Mapped[int] = mapped_column(Integer, default=0)
    total_gasto: Mapped[float] = mapped_column(Float, default=0.0)
    segmento: Mapped[str] = mapped_column(String(20), default="novo")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    ultimo_pedido: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    enderecos: Mapped[list[Endereco]] = relationship(
        "Endereco", back_populates="cliente", cascade="all, delete-orphan"
    )


class Endereco(Base):
    __tablename__ = "enderecos"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    endereco: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    cliente: Mapped[Cliente] = relationship("Cliente", back_populates="enderecos")