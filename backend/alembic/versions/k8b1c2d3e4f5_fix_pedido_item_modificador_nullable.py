"""pedido_item_modificadores.modificador_id → nullable

Revision ID: k8b1c2d3e4f5
Revises: j7a0b1c2d3e4
Branch labels: None
Depends on: None

Contexto:
  Ao deletar um GrupoModificador, o cascade apaga os Modificador filhos.
  Se algum pedido histórico referencia esses modificadores via
  pedido_item_modificadores.modificador_id (FK sem ondelete), o SQLite
  (com PRAGMA foreign_keys=ON) lança IntegrityError antes de completar
  o DELETE — resultando em erro 500 no backend.

Fix:
  Tornar modificador_id nullable. O serviço de deleção anula as
  referências antes de deletar os modificadores, preservando snapshots
  históricos (nome_snapshot, preco_snapshot permanecm intactos).

  Nota: ondelete="SET NULL" no FK nível DB não é configurável via
  batch_alter_table no SQLite sem constraint nomeada. A proteção é
  garantida pelo service layer (cardapio_service.deletar_grupo_modificador).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'k8b1c2d3e4f5'
down_revision: Union[str, None] = 'j7a0b1c2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite não suporta ALTER COLUMN direto; batch_alter recria a tabela.
    # recreate='always' garante que a coluna seja recriada como nullable.
    with op.batch_alter_table('pedido_item_modificadores', recreate='always') as batch_op:
        batch_op.alter_column(
            'modificador_id',
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    # Zera referências a modificadores inexistentes antes de tornar NOT NULL
    op.execute("""
        UPDATE pedido_item_modificadores
        SET modificador_id = 0
        WHERE modificador_id IS NULL
           OR modificador_id NOT IN (SELECT id FROM modificadores)
    """)

    with op.batch_alter_table('pedido_item_modificadores', recreate='always') as batch_op:
        batch_op.alter_column(
            'modificador_id',
            existing_type=sa.Integer(),
            nullable=False,
        )
