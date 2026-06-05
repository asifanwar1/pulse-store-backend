"""repair_order_payment_method_column

Revision ID: 7d9c4a1e6b2f
Revises: 2b7f4c8d1a3e
Create Date: 2026-06-05

"""
from typing import Sequence, Union

from alembic import op


revision: str = "7d9c4a1e6b2f"
down_revision: Union[str, None] = "2b7f4c8d1a3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'paymentmethod') THEN
                CREATE TYPE paymentmethod AS ENUM ('card', 'cod', 'bank_transfer');
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        ALTER TABLE orders
        ADD COLUMN IF NOT EXISTS payment_method paymentmethod NOT NULL DEFAULT 'cod'
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS payment_method")
