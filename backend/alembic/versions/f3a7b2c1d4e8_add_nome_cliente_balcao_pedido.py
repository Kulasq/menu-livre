"""add nome_cliente_balcao pedido

Revision ID: f3a7b2c1d4e8
Revises: e2f5a1c8d3b9
Create Date: 2026-04-23 20:00:00.000000

Adiciona coluna nullable nome_cliente_balcao em pedidos.
Usada para pedidos de balcao onde o cliente e o sistema "Balcao"
mas o admin pode registrar um nome opcional para identificacao do pedido.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a7b2c1d4e8'
down_revision: Union[str, None] = 'e2f5a1c8d3b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('pedidos') as batch_op:
        batch_op.add_column(
            sa.Column('nome_cliente_balcao', sa.String(100), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('pedidos') as batch_op:
        batch_op.drop_column('nome_cliente_balcao')
