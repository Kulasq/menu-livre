"""cliente telefone nullable

Revision ID: g4b8c3d2e1f9
Revises: f3a7b2c1d4e8
Branch labels: None
Depends on: None

Torna telefone nullable em clientes para permitir cadastros no PDV
feitos apenas pelo nome (sem telefone disponível no momento).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'g4b8c3d2e1f9'
down_revision: Union[str, None] = 'f3a7b2c1d4e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('clientes') as batch_op:
        batch_op.alter_column('telefone', existing_type=sa.String(20), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('clientes') as batch_op:
        batch_op.alter_column('telefone', existing_type=sa.String(20), nullable=False)
