"""add_order_notes_column

Revision ID: c3e8f5a1b2d4
Revises: b9c2d1e4a7f0
Create Date: 2026-05-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3e8f5a1b2d4"
down_revision: Union[str, None] = "b9c2d1e4a7f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "notes")
