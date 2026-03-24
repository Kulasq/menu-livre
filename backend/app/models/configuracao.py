from __future__ import annotations
from sqlalchemy import String, Boolean, DateTime, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from app.database import Base


class Configuracao(Base):
    __tablename__ = "configuracoes"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    nome_loja: Mapped[str] = mapped_column(String(100), default="Pão de Mão")
    logo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    banner_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp: Mapped[str] = mapped_column(String(20), nullable=False)
    chave_pix: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tipo_chave_pix: Mapped[str | None] = mapped_column(String(20), nullable=True)
    taxa_entrega: Mapped[float] = mapped_column(Float, default=0.0)
    pedido_minimo: Mapped[float] = mapped_column(Float, default=0.0)
    tempo_entrega_min: Mapped[int] = mapped_column(Integer, default=30)
    tempo_entrega_max: Mapped[int] = mapped_column(Integer, default=50)
    aceitar_pedidos: Mapped[bool] = mapped_column(Boolean, default=True)
    mensagem_fechado: Mapped[str] = mapped_column(
        Text, default="Estamos fechados no momento."
    )
    instagram_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    horarios_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )