"""grupo_modificador: adiciona coluna ativo

Revision ID: j7a0b1c2d3e4
Revises: i6d7e8f9a0b1
Branch labels: None
Depends on: None

Adiciona campo `ativo` (Boolean, default True) em grupos_modificadores.
Grupos existentes ficam ativos por padrão.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'j7a0b1c2d3e4'
down_revision: Union[str, None] = 'i6d7e8f9a0b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite exige batch_alter para adicionar colunas com constraints
    with op.batch_alter_table('grupos_modificadores', recreate='always') as batch_op:
        batch_op.add_column(
            sa.Column('ativo', sa.Boolean(), nullable=False, server_default='1')
        )


def downgrade() -> None:
    with op.batch_alter_table('grupos_modificadores', recreate='always') as batch_op:
        batch_op.drop_column('ativo')
