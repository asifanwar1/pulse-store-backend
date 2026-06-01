"""add_product_total_sales_and_rating

Revision ID: e8b7f3a6c2d1
Revises: d7a9c2f4b8e1
Create Date: 2026-06-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8b7f3a6c2d1"
down_revision: Union[str, None] = "d7a9c2f4b8e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("total_sales", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("products", sa.Column("rating", sa.Integer(), nullable=True))
    op.alter_column("products", "total_sales", server_default=None)


def downgrade() -> None:
    op.drop_column("products", "rating")
    op.drop_column("products", "total_sales")
