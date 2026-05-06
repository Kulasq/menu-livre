"""modificadores: adiciona campos de controle de estoque

Revision ID: n1e4f5a6b7c8
Revises: m0d3e4f5a6b7
Branch labels: None
Depends on: None
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op


revision: str = 'n1e4f5a6b7c8'
down_revision: Union[str, None] = 'm0d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    colunas = [c['name'] for c in inspector.get_columns('modificadores')]

    if 'controle_estoque' not in colunas:
        op.add_column('modificadores', sa.Column('controle_estoque', sa.Boolean(), nullable=False, server_default='0'))
    if 'estoque_atual' not in colunas:
        op.add_column('modificadores', sa.Column('estoque_atual', sa.Integer(), nullable=False, server_default='0'))
    if 'estoque_minimo' not in colunas:
        op.add_column('modificadores', sa.Column('estoque_minimo', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    with op.batch_alter_table('modificadores') as batch_op:
        batch_op.drop_column('estoque_minimo')
        batch_op.drop_column('estoque_atual')
        batch_op.drop_column('controle_estoque')
