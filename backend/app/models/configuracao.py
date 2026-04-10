from __future__ import annotations
from sqlalchemy import String, Boolean, DateTime, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from app.database import Base

# Paleta padrão Menu Livre (espelha o admin.css)
_COR_PRIMARIA_DEFAULT  = "#f59e0b"   # --accent
_COR_SECUNDARIA_DEFAULT = "#d97706"  # --accent-hover
_COR_FUNDO_DEFAULT     = "#f1f5f9"   # --bg
_COR_FONTE_DEFAULT     = "#0f172a"   # --texto
_COR_BANNER_DEFAULT    = "#0f172a"   # --bg-sidebar


class Configuracao(Base):
    __tablename__ = "configuracoes"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    nome_loja: Mapped[str] = mapped_column(String(100), default="Minha Loja")
    logo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    banner_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp: Mapped[str] = mapped_column(String(20), nullable=False)
    chave_pix: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tipo_chave_pix: Mapped[str | None] = mapped_column(String(20), nullable=True)
    taxa_entrega: Mapped[float] = mapped_column(Float, default=0.0)
    pedido_minimo: Mapped[float] = mapped_column(Float, default=0.0)
    tempo_entrega_min: Mapped[int] = mapped_column(Integer, default=30)
    tempo_entrega_max: Mapped[int] = mapped_column(Integer, default=50)
    fechado_manualmente: Mapped[bool] = mapped_column(Boolean, default=False)
    aceitar_agendamentos: Mapped[bool] = mapped_column(Boolean, default=True)
    limite_agendamentos: Mapped[int] = mapped_column(Integer, default=10)
    mensagem_fechado: Mapped[str] = mapped_column(
        Text, default="Estamos fechados no momento."
    )
    instagram_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    horarios_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Aparência do cardápio público ────────────────────────────────────────
    # Valores armazenados como hex (#rrggbb). O admin pode salvar qualquer
    # formato CSS válido — o service normaliza para hex antes de persistir.
    cor_primaria: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default=_COR_PRIMARIA_DEFAULT
    )
    cor_secundaria: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default=_COR_SECUNDARIA_DEFAULT
    )
    cor_fundo: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default=_COR_FUNDO_DEFAULT
    )
    cor_fonte: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default=_COR_FONTE_DEFAULT
    )
    cor_banner: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default=_COR_BANNER_DEFAULT
    )

    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )