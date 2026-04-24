"""add tipo balcao pedido

Revision ID: e2f5a1c8d3b9
Revises: d1e9f2a4b3c7
Create Date: 2026-04-22 22:00:00.000000

Adiciona o valor 'balcao' ao campo tipo de pedidos.
No SQLite o campo tipo é VARCHAR sem check constraint rígida,
portanto não há DDL a executar — a migration é um marcador
para documentar a mudança de domínio e permitir rollback limpo.

Em bancos com CHECK CONSTRAINT explícita (PostgreSQL, MySQL)
seria necessário adicionar o novo valor ao enum.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e2f5a1c8d3b9'
down_revision: Union[str, None] = 'd1e9f2a4b3c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite: tipo é VARCHAR(20) sem check constraint — nenhum DDL necessário.
    # O backend já aceitará 'balcao' como valor válido após atualização do schema.
    pass


def downgrade() -> None:
    # Não há DDL a reverter. Pedidos com tipo='balcao' precisariam
    # ser migrados manualmente antes do downgrade em produção.
    pass
