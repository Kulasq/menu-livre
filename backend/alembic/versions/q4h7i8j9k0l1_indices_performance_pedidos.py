"""pedidos: indices de performance (status, status_pagamento, criado_em)

Revision ID: q4h7i8j9k0l1
Revises: p3g6h7i8j9k0
Branch labels: None
Depends on: None
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op


revision: str = 'q4h7i8j9k0l1'
down_revision: Union[str, None] = 'p3g6h7i8j9k0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Nomes seguem a convenção padrão do SQLAlchemy (ix_%(table)s_%(column)s),
# para casar com o index=True declarado no model Pedido.
_INDICES = (
    ("ix_pedidos_status", "status"),
    ("ix_pedidos_status_pagamento", "status_pagamento"),
    ("ix_pedidos_criado_em", "criado_em"),
)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existentes = {ix["name"] for ix in inspector.get_indexes("pedidos")}

    for nome, coluna in _INDICES:
        if nome not in existentes:
            op.create_index(nome, "pedidos", [coluna])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existentes = {ix["name"] for ix in inspector.get_indexes("pedidos")}

    for nome, _coluna in _INDICES:
        if nome in existentes:
            op.drop_index(nome, table_name="pedidos")
