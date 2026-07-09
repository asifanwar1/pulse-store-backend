"""add_favourites_table

Revision ID: c5e2a9f7d4b6
Revises: a2c7e9f1d4b6
Create Date: 2026-07-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c5e2a9f7d4b6"
down_revision: Union[str, None] = "a2c7e9f1d4b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "favourites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_favourites_user_product"),
    )
    op.create_index(op.f("ix_favourites_id"), "favourites", ["id"], unique=False)
    op.create_index(op.f("ix_favourites_user_id"), "favourites", ["user_id"], unique=False)
    op.create_index(op.f("ix_favourites_product_id"), "favourites", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_favourites_product_id"), table_name="favourites")
    op.drop_index(op.f("ix_favourites_user_id"), table_name="favourites")
    op.drop_index(op.f("ix_favourites_id"), table_name="favourites")
    op.drop_table("favourites")
