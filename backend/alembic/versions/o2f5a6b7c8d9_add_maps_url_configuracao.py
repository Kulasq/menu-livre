"""configuracao: adiciona campo maps_url

Revision ID: o2f5a6b7c8d9
Revises: n1e4f5a6b7c8
Branch labels: None
Depends on: None
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op


revision: str = 'o2f5a6b7c8d9'
down_revision: Union[str, None] = 'n1e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    colunas = [c['name'] for c in inspector.get_columns('configuracoes')]

    if 'maps_url' not in colunas:
        op.add_column('configuracoes', sa.Column('maps_url', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('configuracoes') as batch_op:
        batch_op.drop_column('maps_url')
