"""pedido cliente_id nullable set null

Revision ID: h5c9d4e3f2a1
Revises: g4b8c3d2e1f9
Branch labels: None
Depends on: None

Torna pedidos.cliente_id nullable com ON DELETE SET NULL.
Ao excluir um cliente, seus pedidos ficam com cliente_id=NULL
preservando o histórico de pedidos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'h5c9d4e3f2a1'
down_revision: Union[str, None] = 'g4b8c3d2e1f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('pedidos', recreate='always') as batch_op:
        batch_op.alter_column(
            'cliente_id',
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.create_foreign_key(
            'fk_pedidos_cliente_id_setnull',
            'clientes',
            ['cliente_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    with op.batch_alter_table('pedidos', recreate='always') as batch_op:
        batch_op.alter_column(
            'cliente_id',
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.create_foreign_key(
            'fk_pedidos_cliente_id',
            'clientes',
            ['cliente_id'],
            ['id'],
        )
