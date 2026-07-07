"""add_wallet_tables_and_order_payment_status

Revision ID: a2c7e9f1d4b6
Revises: f1a4c8e6b3d2
Create Date: 2026-07-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a2c7e9f1d4b6"
down_revision: Union[str, None] = "f1a4c8e6b3d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


order_payment_status = postgresql.ENUM("UNPAID", "PAID", "REFUNDED", name="orderpaymentstatus")
order_payment_status_existing = postgresql.ENUM(
    "UNPAID", "PAID", "REFUNDED", name="orderpaymentstatus", create_type=False
)

wallet_payment_status = postgresql.ENUM(
    "SUCCEEDED", "FAILED", "REQUIRES_ACTION", "PROCESSING", name="paymentstatus"
)
wallet_payment_status_existing = postgresql.ENUM(
    "SUCCEEDED", "FAILED", "REQUIRES_ACTION", "PROCESSING", name="paymentstatus", create_type=False
)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        # SQLAlchemy's Enum type persists the Python enum member's *name*
        # (lowercase, matching the existing 'card'/'cod'/'bank_transfer'
        # labels below), not its .value -- so the new label must be lowercase.
        op.execute("ALTER TYPE paymentmethod ADD VALUE IF NOT EXISTS 'wallet'")

    order_payment_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "orders",
        sa.Column("payment_status", order_payment_status_existing, nullable=False, server_default="UNPAID"),
    )

    wallet_payment_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "wallets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("stripe_customer_id"),
    )
    op.create_index(op.f("ix_wallets_id"), "wallets", ["id"], unique=False)

    op.create_table(
        "wallet_payment_methods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column("stripe_payment_method_id", sa.String(), nullable=False),
        sa.Column("brand", sa.String(), nullable=False),
        sa.Column("last4", sa.String(), nullable=False),
        sa.Column("exp_month", sa.Integer(), nullable=False),
        sa.Column("exp_year", sa.Integer(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_payment_method_id"),
    )
    op.create_index(op.f("ix_wallet_payment_methods_id"), "wallet_payment_methods", ["id"], unique=False)
    op.create_index(op.f("ix_wallet_payment_methods_wallet_id"), "wallet_payment_methods", ["wallet_id"], unique=False)

    op.create_table(
        "wallet_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("stripe_payment_intent_id", sa.String(), nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="usd"),
        sa.Column("status", wallet_payment_status_existing, nullable=False),
        sa.Column("failure_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["wallet_id"], ["wallets.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_payment_intent_id"),
    )
    op.create_index(op.f("ix_wallet_transactions_id"), "wallet_transactions", ["id"], unique=False)
    op.create_index(op.f("ix_wallet_transactions_wallet_id"), "wallet_transactions", ["wallet_id"], unique=False)
    op.create_index(op.f("ix_wallet_transactions_order_id"), "wallet_transactions", ["order_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_wallet_transactions_order_id"), table_name="wallet_transactions")
    op.drop_index(op.f("ix_wallet_transactions_wallet_id"), table_name="wallet_transactions")
    op.drop_index(op.f("ix_wallet_transactions_id"), table_name="wallet_transactions")
    op.drop_table("wallet_transactions")

    op.drop_index(op.f("ix_wallet_payment_methods_wallet_id"), table_name="wallet_payment_methods")
    op.drop_index(op.f("ix_wallet_payment_methods_id"), table_name="wallet_payment_methods")
    op.drop_table("wallet_payment_methods")

    op.drop_index(op.f("ix_wallets_id"), table_name="wallets")
    op.drop_table("wallets")

    wallet_payment_status.drop(op.get_bind(), checkfirst=True)

    op.drop_column("orders", "payment_status")
    order_payment_status.drop(op.get_bind(), checkfirst=True)

    # Postgres cannot drop a single enum value; the 'WALLET' addition to
    # paymentmethod is intentionally irreversible (same convention as
    # 9d2e5a7c1b44_add_shipping_order_status.py).
