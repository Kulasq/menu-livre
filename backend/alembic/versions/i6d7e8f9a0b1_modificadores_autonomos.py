"""modificadores autônomos — M:N produto-grupo

Revision ID: i6d7e8f9a0b1
Revises: h5c9d4e3f2a1
Branch labels: None
Depends on: None

Cria tabela produto_grupo_modificador (M:N).
Migra vínculos existentes (produto_id + ordem do grupo → junction).
Dropa colunas produto_id e ordem de grupos_modificadores.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'i6d7e8f9a0b1'
down_revision: Union[str, None] = 'h5c9d4e3f2a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import text

    conn = op.get_bind()

    # Verifica se a junction table já existe (pode ter sido criada via create_all
    # quando o servidor subiu com o novo model antes de a migration rodar).
    tabelas_existentes = {
        r[0] for r in conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
    }

    if 'produto_grupo_modificador' not in tabelas_existentes:
        op.create_table(
            'produto_grupo_modificador',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('produto_id', sa.Integer(), nullable=False),
            sa.Column('grupo_id', sa.Integer(), nullable=False),
            sa.Column('ordem', sa.Integer(), nullable=False, server_default='0'),
            sa.ForeignKeyConstraint(['grupo_id'], ['grupos_modificadores.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['produto_id'], ['produtos.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('produto_id', 'grupo_id', name='uq_produto_grupo'),
        )
        op.create_index('ix_produto_grupo_modificador_grupo_id', 'produto_grupo_modificador', ['grupo_id'])
        op.create_index('ix_produto_grupo_modificador_produto_id', 'produto_grupo_modificador', ['produto_id'])

        # Migra vínculos existentes para a junction table (só quando cria do zero)
        op.execute("""
            INSERT INTO produto_grupo_modificador (produto_id, grupo_id, ordem)
            SELECT produto_id, id, ordem
            FROM grupos_modificadores
            WHERE produto_id IS NOT NULL
        """)

    # Dropa produto_id e ordem de grupos_modificadores — sempre necessário.
    # Verifica se as colunas ainda existem antes de dropar (idempotência).
    colunas_gm = {
        r[1] for r in conn.execute(text("PRAGMA table_info(grupos_modificadores)"))
    }

    if 'produto_id' in colunas_gm or 'ordem' in colunas_gm:
        # SQLite exige batch_alter para dropar colunas.
        # O índice ix_grupos_modificadores_produto_id precisa ser dropado
        # explicitamente antes do recreate.
        indices_gm = {
            r[0] for r in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='grupos_modificadores'")
            )
        }
        with op.batch_alter_table('grupos_modificadores', recreate='always') as batch_op:
            if 'ix_grupos_modificadores_produto_id' in indices_gm:
                batch_op.drop_index('ix_grupos_modificadores_produto_id')
            if 'produto_id' in colunas_gm:
                batch_op.drop_column('produto_id')
            if 'ordem' in colunas_gm:
                batch_op.drop_column('ordem')


def downgrade() -> None:
    with op.batch_alter_table('grupos_modificadores', recreate='always') as batch_op:
        batch_op.add_column(sa.Column('produto_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('ordem', sa.Integer(), nullable=False, server_default='0'))

    # Restaura produto_id e ordem do primeiro vínculo (perda aceitável em downgrade)
    op.execute("""
        UPDATE grupos_modificadores
        SET produto_id = (
            SELECT produto_id FROM produto_grupo_modificador
            WHERE grupo_id = grupos_modificadores.id
            LIMIT 1
        ),
        ordem = (
            SELECT ordem FROM produto_grupo_modificador
            WHERE grupo_id = grupos_modificadores.id
            LIMIT 1
        )
    """)

    op.drop_index('ix_produto_grupo_modificador_grupo_id', 'produto_grupo_modificador')
    op.drop_index('ix_produto_grupo_modificador_produto_id', 'produto_grupo_modificador')
    op.drop_table('produto_grupo_modificador')
