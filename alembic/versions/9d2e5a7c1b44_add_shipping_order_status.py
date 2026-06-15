"""add_shipping_order_status

Revision ID: 9d2e5a7c1b44
Revises: 8b6d4f2a9c31
Create Date: 2026-06-15

"""
from typing import Sequence, Union

from alembic import op


revision: str = "9d2e5a7c1b44"
down_revision: Union[str, None] = "8b6d4f2a9c31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'SHIPPING' AFTER 'PROCESSING'")


def downgrade() -> None:
    pass
