"""add_user_status

Revision ID: 2b7f4c8d1a3e
Revises: 9c1a7b2e4d6f
Create Date: 2026-06-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2b7f4c8d1a3e"
down_revision: Union[str, None] = "9c1a7b2e4d6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("status", sa.String(), nullable=True))
    op.execute(
        """
        UPDATE users
        SET status = CASE
            WHEN is_active IS TRUE THEN 'ACTIVE'
            ELSE 'INACTIVE'
        END
        WHERE status IS NULL
        """
    )
    op.alter_column("users", "status", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "status")
