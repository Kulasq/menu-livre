from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.database import Base

if TYPE_CHECKING:
    from app.models.pedido import Pedido
    from app.models.produto import Produto


class Cupom(Base):
    __tablename__ = "cupons"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    # Tipos: percentual | valor_fixo | frete_gratis | brinde
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    # Valor do desconto: % se tipo=percentual, R$ se tipo=valor_fixo, 0 nos demais
    valor: Mapped[float] = mapped_column(Float, default=0.0)
    # Teto em R$ para cupons percentuais (ex: 10% até R$20). Null = sem teto
    desconto_maximo: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Para tipo=brinde: produto que será adicionado gratuitamente
    produto_brinde_id: Mapped[int | None] = mapped_column(
        ForeignKey("produtos.id", ondelete="SET NULL"), nullable=True
    )
    # Elegibilidade
    valor_minimo_pedido: Mapped[float] = mapped_column(Float, default=0.0)
    limite_total_usos: Mapped[int | None] = mapped_column(Integer, nullable=True)  # null = ilimitado
    usos_atuais: Mapped[int] = mapped_column(Integer, default=0)
    # 0 = sem limite por cliente; 1 = uma vez por telefone
    limite_por_cliente: Mapped[int] = mapped_column(Integer, default=0)
    somente_primeira_compra: Mapped[bool] = mapped_column(Boolean, default=False)
    # Janela de validade (null = sem restrição)
    data_inicio: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    data_fim: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Toggle manual — não deleta, só desativa
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    produto_brinde: Mapped[Produto | None] = relationship("Produto", lazy="select")
    usos: Mapped[list[CupomUso]] = relationship(
        "CupomUso", back_populates="cupom", cascade="all, delete-orphan"
    )


class CupomUso(Base):
    """Registro imutável de cada uso de cupom. Serve para auditoria,
    contagem 'limit by cliente' e relatório de faturamento gerado."""
    __tablename__ = "cupom_usos"

    id: Mapped[int] = mapped_column(primary_key=True)
    cupom_id: Mapped[int] = mapped_column(
        ForeignKey("cupons.id", ondelete="CASCADE"), index=True, nullable=False
    )
    pedido_id: Mapped[int] = mapped_column(
        ForeignKey("pedidos.id", ondelete="CASCADE"), index=True, nullable=False
    )
    cliente_telefone: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    # Valor efetivo descontado neste pedido (em R$)
    desconto_aplicado: Mapped[float] = mapped_column(Float, nullable=False)
    # Snapshot do subtotal no momento do uso (para calcular faturamento gerado)
    subtotal_pedido: Mapped[float] = mapped_column(Float, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    cupom: Mapped[Cupom] = relationship("Cupom", back_populates="usos")
