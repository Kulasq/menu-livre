"""pedido_itens: registra fix de deleção de produto com pedidos históricos

Revision ID: l9c2d3e4f5a6
Revises: k8b1c2d3e4f5
Branch labels: None
Depends on: None

Contexto:
  Com PRAGMA foreign_keys=ON, deletar um produto que tem pedidos históricos
  causava IntegrityError porque pedido_itens.produto_id não tinha ON DELETE SET NULL
  no nível do banco.

  SQLite não suporta alterar FKs de tabelas existentes sem recriá-las do zero.
  A proteção é garantida pelo service layer: cardapio_service.deletar_produto()
  anula pedido_itens.produto_id (e variante_id via cascade de variantes)
  antes de executar o DELETE, eliminando as referências.

  Este migration não altera schema — serve como checkpoint no histórico do Alembic.
"""
from typing import Sequence, Union


revision: str = 'l9c2d3e4f5a6'
down_revision: Union[str, None] = 'k8b1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
