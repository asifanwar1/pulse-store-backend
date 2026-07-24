"""add_conversation_created_product_id

Revision ID: b3f7e91a4c28
Revises: a1b2c3d4e5f6
Create Date: 2026-07-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3f7e91a4c28"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_conversations",
        sa.Column("created_product_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_ai_conversations_created_product_id_products",
        "ai_conversations",
        "products",
        ["created_product_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_ai_conversations_created_product_id_products", "ai_conversations", type_="foreignkey"
    )
    op.drop_column("ai_conversations", "created_product_id")
