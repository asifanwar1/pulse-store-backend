"""add_order_shipping_fee

Revision ID: b7d3f9a1c5e8
Revises: e4a9f2c7b1d6
Create Date: 2026-07-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7d3f9a1c5e8"
down_revision: Union[str, None] = "e4a9f2c7b1d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "shipping_fee",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="5.99",
        ),
    )
    # Drop the server default after backfilling existing rows so future inserts
    # rely on the application-side default instead (matches other money columns).
    op.alter_column("orders", "shipping_fee", server_default=None)


def downgrade() -> None:
    op.drop_column("orders", "shipping_fee")
