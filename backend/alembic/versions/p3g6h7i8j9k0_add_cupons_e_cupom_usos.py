"""cupons: cria tabelas cupons e cupom_usos, adiciona colunas de cupom em pedidos

Revision ID: p3g6h7i8j9k0
Revises: o2f5a6b7c8d9
Branch labels: None
Depends on: None
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op


revision: str = 'p3g6h7i8j9k0'
down_revision: Union[str, None] = 'o2f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tabelas_existentes = inspector.get_table_names()

    # ── Tabela cupons ────────────────────────────────────────────────────────
    if 'cupons' not in tabelas_existentes:
        op.create_table(
            'cupons',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('codigo', sa.String(50), nullable=False, unique=True),
            sa.Column('tipo', sa.String(20), nullable=False),
            sa.Column('valor', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('desconto_maximo', sa.Float(), nullable=True),
            sa.Column('produto_brinde_id', sa.Integer(), sa.ForeignKey('produtos.id', ondelete='SET NULL'), nullable=True),
            sa.Column('valor_minimo_pedido', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('limite_total_usos', sa.Integer(), nullable=True),
            sa.Column('usos_atuais', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('limite_por_cliente', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('somente_primeira_compra', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('data_inicio', sa.DateTime(), nullable=True),
            sa.Column('data_fim', sa.DateTime(), nullable=True),
            sa.Column('ativo', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('criado_em', sa.DateTime(), nullable=False),
            sa.Column('atualizado_em', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_cupons_codigo', 'cupons', ['codigo'])

    # ── Tabela cupom_usos ────────────────────────────────────────────────────
    if 'cupom_usos' not in tabelas_existentes:
        op.create_table(
            'cupom_usos',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('cupom_id', sa.Integer(), sa.ForeignKey('cupons.id', ondelete='CASCADE'), nullable=False),
            sa.Column('pedido_id', sa.Integer(), sa.ForeignKey('pedidos.id', ondelete='CASCADE'), nullable=False),
            sa.Column('cliente_telefone', sa.String(20), nullable=True),
            sa.Column('desconto_aplicado', sa.Float(), nullable=False),
            sa.Column('subtotal_pedido', sa.Float(), nullable=False),
            sa.Column('criado_em', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_cupom_usos_cupom_id', 'cupom_usos', ['cupom_id'])
        op.create_index('ix_cupom_usos_pedido_id', 'cupom_usos', ['pedido_id'])
        op.create_index('ix_cupom_usos_cliente_telefone', 'cupom_usos', ['cliente_telefone'])

    # ── Colunas novas em pedidos ─────────────────────────────────────────────
    colunas_pedidos = [c['name'] for c in inspector.get_columns('pedidos')]

    if 'cupom_id' not in colunas_pedidos:
        op.add_column('pedidos', sa.Column('cupom_id', sa.Integer(), nullable=True))
        # Adicionar FK manualmente via batch (SQLite exige batch para ALTER TABLE)
        with op.batch_alter_table('pedidos') as batch_op:
            batch_op.create_foreign_key(
                'fk_pedidos_cupom_id',
                'cupons',
                ['cupom_id'],
                ['id'],
                ondelete='SET NULL',
            )

    if 'cupom_codigo' not in colunas_pedidos:
        op.add_column('pedidos', sa.Column('cupom_codigo', sa.String(50), nullable=True))

    if 'desconto_cupom' not in colunas_pedidos:
        op.add_column('pedidos', sa.Column('desconto_cupom', sa.Float(), nullable=False, server_default='0.0'))


def downgrade() -> None:
    with op.batch_alter_table('pedidos') as batch_op:
        batch_op.drop_constraint('fk_pedidos_cupom_id', type_='foreignkey')
        batch_op.drop_column('desconto_cupom')
        batch_op.drop_column('cupom_codigo')
        batch_op.drop_column('cupom_id')

    op.drop_index('ix_cupom_usos_cliente_telefone', 'cupom_usos')
    op.drop_index('ix_cupom_usos_pedido_id', 'cupom_usos')
    op.drop_index('ix_cupom_usos_cupom_id', 'cupom_usos')
    op.drop_table('cupom_usos')

    op.drop_index('ix_cupons_codigo', 'cupons')
    op.drop_table('cupons')
