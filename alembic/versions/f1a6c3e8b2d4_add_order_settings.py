"""add_order_settings

Revision ID: f1a6c3e8b2d4
Revises: d4e8a2c6f193
Create Date: 2026-07-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a6c3e8b2d4"
down_revision: Union[str, None] = "d4e8a2c6f193"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    order_settings = op.create_table(
        "order_settings",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("shipping_fee", sa.Numeric(10, 2), nullable=False),
        sa.Column("updated_by", sa.Integer(),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        order_settings,
        [{"id": 1, "shipping_fee": "5.99"}],
    )


def downgrade() -> None:
    op.drop_table("order_settings")
