"""add_category_image

Revision ID: 3a9d5f7c2e14
Revises: 1f7a6c3e9b52
Create Date: 2026-07-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3a9d5f7c2e14"
down_revision: Union[str, None] = "1f7a6c3e9b52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("image", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("categories", "image")
