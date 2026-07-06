"""add_offers_tables

Revision ID: f1a4c8e6b3d2
Revises: b4f9c2d8e6a1
Create Date: 2026-07-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f1a4c8e6b3d2"
down_revision: Union[str, None] = "b4f9c2d8e6a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


offer_scope = postgresql.ENUM("ALL_CATEGORIES", "SPECIFIC_CATEGORIES", name="offerscope")
offer_scope_existing = postgresql.ENUM(
    "ALL_CATEGORIES", "SPECIFIC_CATEGORIES", name="offerscope", create_type=False
)


def upgrade() -> None:
    offer_scope.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("discount_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("scope", offer_scope_existing, nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_offers_id"), "offers", ["id"], unique=False)
    op.create_index(op.f("ix_offers_name"), "offers", ["name"], unique=False)

    op.create_table(
        "offer_categories",
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("offer_id", "category_id"),
    )

    op.create_table(
        "offer_products",
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("is_excluded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("offer_id", "product_id"),
    )


def downgrade() -> None:
    op.drop_table("offer_products")
    op.drop_table("offer_categories")
    op.drop_index(op.f("ix_offers_name"), table_name="offers")
    op.drop_index(op.f("ix_offers_id"), table_name="offers")
    op.drop_table("offers")
    offer_scope.drop(op.get_bind(), checkfirst=True)
