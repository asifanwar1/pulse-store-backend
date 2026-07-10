"""add_review_visibility_and_derive_rating

Revision ID: 1f7a6c3e9b52
Revises: c5e2a9f7d4b6
Create Date: 2026-07-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1f7a6c3e9b52"
down_revision: Union[str, None] = "c5e2a9f7d4b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "product_reviews",
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_unique_constraint(
        "uq_product_reviews_product_id_user_id", "product_reviews", ["product_id", "user_id"]
    )
    op.alter_column(
        "products",
        "rating",
        existing_type=sa.Integer(),
        type_=sa.Numeric(3, 2),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "products",
        "rating",
        existing_type=sa.Numeric(3, 2),
        type_=sa.Integer(),
        existing_nullable=True,
    )
    op.drop_constraint("uq_product_reviews_product_id_user_id", "product_reviews", type_="unique")
    op.drop_column("product_reviews", "is_hidden")
