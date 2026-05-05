"""configuracoes: adiciona coluna endereco para exibição no cardápio público

Revision ID: m0d3e4f5a6b7
Revises: l9c2d3e4f5a6
Branch labels: None
Depends on: None
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op


revision: str = 'm0d3e4f5a6b7'
down_revision: Union[str, None] = 'l9c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('configuracoes', sa.Column('endereco', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('configuracoes', 'endereco')
