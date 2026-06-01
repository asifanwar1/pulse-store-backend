"""add_product_reviews_table

Revision ID: d7a9c2f4b8e1
Revises: c3e8f5a1b2d4
Create Date: 2026-06-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7a9c2f4b8e1"
down_revision: Union[str, None] = "c3e8f5a1b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_reviews_id"), "product_reviews", ["id"], unique=False)
    op.create_index(op.f("ix_product_reviews_product_id"), "product_reviews", ["product_id"], unique=False)
    op.create_index(op.f("ix_product_reviews_user_id"), "product_reviews", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_product_reviews_user_id"), table_name="product_reviews")
    op.drop_index(op.f("ix_product_reviews_product_id"), table_name="product_reviews")
    op.drop_index(op.f("ix_product_reviews_id"), table_name="product_reviews")
    op.drop_table("product_reviews")
