"""add_user_address

Revision ID: 9c1a7b2e4d6f
Revises: e8b7f3a6c2d1
Create Date: 2026-06-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c1a7b2e4d6f"
down_revision: Union[str, None] = "e8b7f3a6c2d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_EMPTY_ADDRESS = (
    '{"street_address":"","city":"","country":"","state":"","zipcode":"","latitude":"","longitude":""}'
)


def upgrade() -> None:
    op.add_column("users", sa.Column("address", sa.JSON(), nullable=True))
    op.execute(f"UPDATE users SET address = '{_EMPTY_ADDRESS}'::json WHERE address IS NULL")
    op.alter_column("users", "address", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "address")
