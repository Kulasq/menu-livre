"""adicionar campos de cores para aparência do cardápio público

Revision ID: b7e4f91a3c2d
Revises: a3c9e1d7f2b8
Create Date: 2026-04-08 00:00:00.000000

Adiciona cor_primaria, cor_secundaria, cor_fundo, cor_fonte e cor_banner
à tabela configuracoes. Defaults espelham a paleta do painel admin (amber/slate).
Rows existentes recebem os defaults via server_default na migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Paleta padrão Menu Livre (espelha admin.css)
_COR_PRIMARIA_DEFAULT   = "#f59e0b"
_COR_SECUNDARIA_DEFAULT = "#d97706"
_COR_FUNDO_DEFAULT      = "#f1f5f9"
_COR_FONTE_DEFAULT      = "#0f172a"
_COR_BANNER_DEFAULT     = "#0f172a"

revision: str = 'b7e4f91a3c2d'
down_revision: Union[str, None] = 'a3c9e1d7f2b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("configuracoes") as batch_op:
        batch_op.add_column(sa.Column(
            "cor_primaria",
            sa.String(20),
            nullable=True,
            server_default=_COR_PRIMARIA_DEFAULT,
        ))
        batch_op.add_column(sa.Column(
            "cor_secundaria",
            sa.String(20),
            nullable=True,
            server_default=_COR_SECUNDARIA_DEFAULT,
        ))
        batch_op.add_column(sa.Column(
            "cor_fundo",
            sa.String(20),
            nullable=True,
            server_default=_COR_FUNDO_DEFAULT,
        ))
        batch_op.add_column(sa.Column(
            "cor_fonte",
            sa.String(20),
            nullable=True,
            server_default=_COR_FONTE_DEFAULT,
        ))
        batch_op.add_column(sa.Column(
            "cor_banner",
            sa.String(20),
            nullable=True,
            server_default=_COR_BANNER_DEFAULT,
        ))

    # Garante que a linha id=1 (se existir) receba os defaults explicitamente
    op.execute(
        "UPDATE configuracoes SET "
        f"cor_primaria = '{_COR_PRIMARIA_DEFAULT}', "
        f"cor_secundaria = '{_COR_SECUNDARIA_DEFAULT}', "
        f"cor_fundo = '{_COR_FUNDO_DEFAULT}', "
        f"cor_fonte = '{_COR_FONTE_DEFAULT}', "
        f"cor_banner = '{_COR_BANNER_DEFAULT}' "
        "WHERE cor_primaria IS NULL OR cor_primaria = ''"
    )


def downgrade() -> None:
    with op.batch_alter_table("configuracoes") as batch_op:
        batch_op.drop_column("cor_banner")
        batch_op.drop_column("cor_fonte")
        batch_op.drop_column("cor_fundo")
        batch_op.drop_column("cor_secundaria")
        batch_op.drop_column("cor_primaria")
