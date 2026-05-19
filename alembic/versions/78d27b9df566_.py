"""empty message

Revision ID: 78d27b9df566
Revises: eb4fe0c9007f
Create Date: 2026-05-11 16:50:13.288734

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '78d27b9df566'
down_revision: Union[str, None] = 'eb4fe0c9007f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "payment_method",
            sa.Enum("card", "cod", "bank_transfer", name="paymentmethod"),
            nullable=False,
            server_default="cod",
        ),
    )


def downgrade() -> None:
    op.drop_column("orders", "payment_method")
