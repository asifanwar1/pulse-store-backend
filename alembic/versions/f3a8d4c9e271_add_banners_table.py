"""add_banners_table

Revision ID: f3a8d4c9e271
Revises: 3a9d5f7c2e14
Create Date: 2026-07-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f3a8d4c9e271"
down_revision: Union[str, None] = "3a9d5f7c2e14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "banners",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=False),
        sa.Column("image_url_mobile", sa.String(), nullable=True),
        sa.Column("design_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("link_type", sa.String(length=20), nullable=False),
        sa.Column("link_value", sa.String(), nullable=True),
        sa.Column("placement", sa.String(length=50), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_banners_id"), "banners", ["id"], unique=False)
    op.create_index(op.f("ix_banners_placement"), "banners", ["placement"], unique=False)
    op.create_index(op.f("ix_banners_is_active"), "banners", ["is_active"], unique=False)
    op.create_index(
        "ix_banners_placement_active_position",
        "banners",
        ["placement", "is_active", "position"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_banners_placement_active_position", table_name="banners")
    op.drop_index(op.f("ix_banners_is_active"), table_name="banners")
    op.drop_index(op.f("ix_banners_placement"), table_name="banners")
    op.drop_index(op.f("ix_banners_id"), table_name="banners")
    op.drop_table("banners")
