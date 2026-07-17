"""add_order_and_shipment_tracking

Revision ID: c9f2a7b4e1d3
Revises: f3a8d4c9e271
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c9f2a7b4e1d3"
down_revision: Union[str, None] = "f3a8d4c9e271"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Reuse the enum types created by the orders/shipments migrations.
order_status = postgresql.ENUM(
    "PENDING",
    "PROCESSING",
    "SHIPPING",
    "SHIPPED",
    "DELIVERED",
    "CANCELLED",
    name="orderstatus",
    create_type=False,
)
shipment_status = postgresql.ENUM(
    "PENDING",
    "PROCESSING",
    "SHIPPED",
    "IN_TRANSIT",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "CANCELLED",
    "RETURNED",
    name="shipmentstatus",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "order_status_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("status", order_status, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_status_history_id"), "order_status_history", ["id"], unique=False)
    op.create_index(op.f("ix_order_status_history_order_id"), "order_status_history", ["order_id"], unique=False)

    op.create_table(
        "shipment_tracking_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shipment_id", sa.Integer(), nullable=False),
        sa.Column("status", shipment_status, nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"]),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shipment_tracking_events_id"), "shipment_tracking_events", ["id"], unique=False)
    op.create_index(
        op.f("ix_shipment_tracking_events_shipment_id"),
        "shipment_tracking_events",
        ["shipment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_shipment_tracking_events_shipment_id"), table_name="shipment_tracking_events")
    op.drop_index(op.f("ix_shipment_tracking_events_id"), table_name="shipment_tracking_events")
    op.drop_table("shipment_tracking_events")

    op.drop_index(op.f("ix_order_status_history_order_id"), table_name="order_status_history")
    op.drop_index(op.f("ix_order_status_history_id"), table_name="order_status_history")
    op.drop_table("order_status_history")
