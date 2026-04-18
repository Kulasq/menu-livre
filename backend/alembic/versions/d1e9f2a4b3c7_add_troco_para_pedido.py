"""add troco_para pedido

Revision ID: d1e9f2a4b3c7
Revises: c5a8d3e9f1b6
Create Date: 2026-04-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd1e9f2a4b3c7'
down_revision: Union[str, None] = 'c5a8d3e9f1b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pedidos', sa.Column('troco_para', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('pedidos', 'troco_para')
