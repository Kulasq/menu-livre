"""criar tabela enderecos

Revision ID: c5a8d3e9f1b6
Revises: b7e4f91a3c2d
Create Date: 2026-04-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5a8d3e9f1b6'
down_revision: Union[str, None] = 'b7e4f91a3c2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'enderecos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('endereco', sa.Text(), nullable=False),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_enderecos_cliente_id', 'enderecos', ['cliente_id'])


def downgrade() -> None:
    op.drop_index('ix_enderecos_cliente_id', table_name='enderecos')
    op.drop_table('enderecos')
