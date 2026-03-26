from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.database import Base

if TYPE_CHECKING:
    from app.models.cliente import Cliente


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    mesa_id: Mapped[int | None] = mapped_column(ForeignKey("mesas.id"), nullable=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    endereco_entrega: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    taxa_entrega: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, nullable=False)
    metodo_pagamento: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status_pagamento: Mapped[str] = mapped_column(String(20), default="pendente")
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    agendado_para: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pontos_gerados: Mapped[int] = mapped_column(Integer, default=0)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    cliente: Mapped[Cliente] = relationship("Cliente", lazy="select")
    itens: Mapped[list[PedidoItem]] = relationship(
        "PedidoItem", back_populates="pedido", cascade="all, delete-orphan"
    )


class PedidoItem(Base):
    __tablename__ = "pedido_itens"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(
        ForeignKey("pedidos.id", ondelete="CASCADE"), index=True
    )
    produto_id: Mapped[int | None] = mapped_column(ForeignKey("produtos.id"), nullable=True)
    variante_id: Mapped[int | None] = mapped_column(ForeignKey("variantes.id"), nullable=True)
    nome_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    preco_snapshot: Mapped[float] = mapped_column(Float, nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, default=1)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)

    pedido: Mapped[Pedido] = relationship("Pedido", back_populates="itens")
    modificadores: Mapped[list[PedidoItemModificador]] = relationship(
        "PedidoItemModificador", back_populates="pedido_item", cascade="all, delete-orphan"
    )


class PedidoItemModificador(Base):
    __tablename__ = "pedido_item_modificadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_item_id: Mapped[int] = mapped_column(
        ForeignKey("pedido_itens.id", ondelete="CASCADE"), index=True
    )
    modificador_id: Mapped[int] = mapped_column(ForeignKey("modificadores.id"))
    nome_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    preco_snapshot: Mapped[float] = mapped_column(Float, nullable=False)

    pedido_item: Mapped[PedidoItem] = relationship("PedidoItem", back_populates="modificadores")