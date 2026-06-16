"""add_unique_shipment_order_guard

Revision ID: b4f9c2d8e6a1
Revises: 9d2e5a7c1b44
Create Date: 2026-06-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4f9c2d8e6a1"
down_revision: Union[str, None] = "9d2e5a7c1b44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    duplicates = op.get_bind().execute(
        sa.text(
            """
            SELECT order_id, COUNT(*) AS shipment_count
            FROM shipments
            GROUP BY order_id
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    if duplicates:
        duplicate_order_ids = ", ".join(str(row.order_id) for row in duplicates)
        raise RuntimeError(
            "Cannot add one-shipment-per-order constraint. "
            f"Duplicate shipments exist for order_id(s): {duplicate_order_ids}"
        )

    op.create_unique_constraint("uq_shipments_order_id", "shipments", ["order_id"])


def downgrade() -> None:
    op.drop_constraint("uq_shipments_order_id", "shipments", type_="unique")
