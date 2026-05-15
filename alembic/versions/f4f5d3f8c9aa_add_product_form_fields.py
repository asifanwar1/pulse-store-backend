"""add_product_form_fields

Revision ID: f4f5d3f8c9aa
Revises: 78d27b9df566
Create Date: 2026-05-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4f5d3f8c9aa"
down_revision: Union[str, None] = "78d27b9df566"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("sku", sa.String(), nullable=True))
    op.add_column("products", sa.Column("brand", sa.String(), nullable=True))
    op.add_column("products", sa.Column("cost_price", sa.Numeric(10, 2), nullable=True))
    op.add_column("products", sa.Column("tags", sa.JSON(), nullable=True))
    op.add_column("products", sa.Column("media", sa.JSON(), nullable=True))

    op.execute("UPDATE products SET sku = CONCAT('SKU-', id) WHERE sku IS NULL")
    op.execute("UPDATE products SET brand = 'UNKNOWN' WHERE brand IS NULL")
    op.execute("UPDATE products SET cost_price = price WHERE cost_price IS NULL")
    op.execute("UPDATE products SET tags = '[]'::json WHERE tags IS NULL")
    op.execute("UPDATE products SET media = '[]'::json WHERE media IS NULL")

    op.alter_column("products", "sku", nullable=False)
    op.alter_column("products", "brand", nullable=False)
    op.alter_column("products", "cost_price", nullable=False)
    op.alter_column("products", "tags", nullable=False)
    op.alter_column("products", "media", nullable=False)
    op.create_index(op.f("ix_products_sku"), "products", ["sku"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_products_sku"), table_name="products")
    op.drop_column("products", "media")
    op.drop_column("products", "tags")
    op.drop_column("products", "cost_price")
    op.drop_column("products", "brand")
    op.drop_column("products", "sku")
