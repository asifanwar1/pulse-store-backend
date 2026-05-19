"""uppercase_order_status_enum_values

Revision ID: b9c2d1e4a7f0
Revises: f4f5d3f8c9aa
Create Date: 2026-05-19

"""
from typing import Sequence, Union

from alembic import op


revision: str = "b9c2d1e4a7f0"
down_revision: Union[str, None] = "f4f5d3f8c9aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE orderstatus RENAME VALUE 'pending' TO 'PENDING'")
    op.execute("ALTER TYPE orderstatus RENAME VALUE 'processing' TO 'PROCESSING'")
    op.execute("ALTER TYPE orderstatus RENAME VALUE 'shipped' TO 'SHIPPED'")
    op.execute("ALTER TYPE orderstatus RENAME VALUE 'delivered' TO 'DELIVERED'")
    op.execute("ALTER TYPE orderstatus RENAME VALUE 'cancelled' TO 'CANCELLED'")


def downgrade() -> None:
    op.execute("ALTER TYPE orderstatus RENAME VALUE 'PENDING' TO 'pending'")
    op.execute("ALTER TYPE orderstatus RENAME VALUE 'PROCESSING' TO 'processing'")
    op.execute("ALTER TYPE orderstatus RENAME VALUE 'SHIPPED' TO 'shipped'")
    op.execute("ALTER TYPE orderstatus RENAME VALUE 'DELIVERED' TO 'delivered'")
    op.execute("ALTER TYPE orderstatus RENAME VALUE 'CANCELLED' TO 'cancelled'")
