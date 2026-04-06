"""controle status loja: separar aceitar_pedidos em fechado_manualmente e aceitar_agendamentos

Revision ID: a3c9e1d7f2b8
Revises: 281db827dfba
Create Date: 2026-04-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3c9e1d7f2b8'
down_revision: Union[str, None] = '281db827dfba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adicionar novos campos antes de remover o antigo
    with op.batch_alter_table("configuracoes") as batch_op:
        batch_op.add_column(sa.Column(
            "fechado_manualmente", sa.Boolean(), nullable=False, server_default="0"
        ))
        batch_op.add_column(sa.Column(
            "aceitar_agendamentos", sa.Boolean(), nullable=False, server_default="1"
        ))
        batch_op.add_column(sa.Column(
            "limite_agendamentos", sa.Integer(), nullable=False, server_default="10"
        ))

    # Migrar dados: se aceitar_pedidos=False → fechado_manualmente=True
    op.execute(
        "UPDATE configuracoes SET fechado_manualmente = CASE WHEN aceitar_pedidos = 0 THEN 1 ELSE 0 END"
    )

    # Remover coluna antiga
    with op.batch_alter_table("configuracoes") as batch_op:
        batch_op.drop_column("aceitar_pedidos")


def downgrade() -> None:
    with op.batch_alter_table("configuracoes") as batch_op:
        batch_op.add_column(sa.Column(
            "aceitar_pedidos", sa.Boolean(), nullable=False, server_default="1"
        ))

    # Migrar dados de volta: fechado_manualmente=True → aceitar_pedidos=False
    op.execute(
        "UPDATE configuracoes SET aceitar_pedidos = CASE WHEN fechado_manualmente = 1 THEN 0 ELSE 1 END"
    )

    with op.batch_alter_table("configuracoes") as batch_op:
        batch_op.drop_column("limite_agendamentos")
        batch_op.drop_column("aceitar_agendamentos")
        batch_op.drop_column("fechado_manualmente")
