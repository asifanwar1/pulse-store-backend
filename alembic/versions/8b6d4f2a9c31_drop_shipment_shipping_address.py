"""drop_shipment_shipping_address

Revision ID: 8b6d4f2a9c31
Revises: 4a8f2d6c9b10
Create Date: 2026-06-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8b6d4f2a9c31"
down_revision: Union[str, None] = "4a8f2d6c9b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("shipments", "shipping_address")


def downgrade() -> None:
    op.add_column("shipments", sa.Column("shipping_address", sa.JSON(), nullable=True))
