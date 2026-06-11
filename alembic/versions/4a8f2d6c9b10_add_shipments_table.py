"""add_shipments_table

Revision ID: 4a8f2d6c9b10
Revises: 7d9c4a1e6b2f
Create Date: 2026-06-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4a8f2d6c9b10"
down_revision: Union[str, None] = "7d9c4a1e6b2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


shipment_method = sa.Enum("STANDARD", "EXPRESS", "OVERNIGHT", "PICKUP", name="shipmentmethod")
shipment_status = sa.Enum(
    "PENDING",
    "PROCESSING",
    "SHIPPED",
    "IN_TRANSIT",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "CANCELLED",
    "RETURNED",
    name="shipmentstatus",
)


def upgrade() -> None:
    shipment_method.create(op.get_bind(), checkfirst=True)
    shipment_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "shipments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("tracking_id", sa.String(), nullable=False),
        sa.Column("shipment_method", shipment_method, nullable=False),
        sa.Column("courier", sa.String(), nullable=False),
        sa.Column("status", shipment_status, nullable=False),
        sa.Column("shipping_address", sa.JSON(), nullable=True),
        sa.Column("estimated_delivery_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shipments_id"), "shipments", ["id"], unique=False)
    op.create_index(op.f("ix_shipments_order_id"), "shipments", ["order_id"], unique=False)
    op.create_index(op.f("ix_shipments_status"), "shipments", ["status"], unique=False)
    op.create_index(op.f("ix_shipments_tracking_id"), "shipments", ["tracking_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_shipments_tracking_id"), table_name="shipments")
    op.drop_index(op.f("ix_shipments_status"), table_name="shipments")
    op.drop_index(op.f("ix_shipments_order_id"), table_name="shipments")
    op.drop_index(op.f("ix_shipments_id"), table_name="shipments")
    op.drop_table("shipments")
    shipment_status.drop(op.get_bind(), checkfirst=True)
    shipment_method.drop(op.get_bind(), checkfirst=True)
