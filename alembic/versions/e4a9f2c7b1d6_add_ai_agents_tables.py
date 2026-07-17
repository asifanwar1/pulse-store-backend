"""add_ai_agents_tables

Revision ID: e4a9f2c7b1d6
Revises: c9f2a7b4e1d3
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e4a9f2c7b1d6"
down_revision: Union[str, None] = "c9f2a7b4e1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_agent_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_key", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("system_prompt_override", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_agent_configs_id"), "ai_agent_configs", ["id"], unique=False)
    op.create_index(op.f("ix_ai_agent_configs_agent_key"), "ai_agent_configs", ["agent_key"], unique=True)

    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_key", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_conversations_id"), "ai_conversations", ["id"], unique=False)
    op.create_index(op.f("ix_ai_conversations_agent_key"), "ai_conversations", ["agent_key"], unique=False)
    op.create_index(op.f("ix_ai_conversations_user_id"), "ai_conversations", ["user_id"], unique=False)

    op.create_table(
        "ai_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("message_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_messages_id"), "ai_messages", ["id"], unique=False)
    op.create_index(op.f("ix_ai_messages_conversation_id"), "ai_messages", ["conversation_id"], unique=False)

    op.create_table(
        "ai_support_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_support_tickets_id"), "ai_support_tickets", ["id"], unique=False)
    op.create_index(op.f("ix_ai_support_tickets_user_id"), "ai_support_tickets", ["user_id"], unique=False)
    op.create_index(op.f("ix_ai_support_tickets_is_resolved"), "ai_support_tickets", ["is_resolved"], unique=False)

    op.bulk_insert(
        sa.table(
            "ai_agent_configs",
            sa.column("agent_key", sa.String()),
            sa.column("display_name", sa.String()),
            sa.column("is_enabled", sa.Boolean()),
        ),
        [
            {"agent_key": "product_listing", "display_name": "Product Listing Assistant", "is_enabled": True},
            {"agent_key": "order_tracking", "display_name": "Order Tracking Assistant", "is_enabled": True},
            {"agent_key": "customer_query", "display_name": "Customer Query Assistant", "is_enabled": True},
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_support_tickets_is_resolved"), table_name="ai_support_tickets")
    op.drop_index(op.f("ix_ai_support_tickets_user_id"), table_name="ai_support_tickets")
    op.drop_index(op.f("ix_ai_support_tickets_id"), table_name="ai_support_tickets")
    op.drop_table("ai_support_tickets")

    op.drop_index(op.f("ix_ai_messages_conversation_id"), table_name="ai_messages")
    op.drop_index(op.f("ix_ai_messages_id"), table_name="ai_messages")
    op.drop_table("ai_messages")

    op.drop_index(op.f("ix_ai_conversations_user_id"), table_name="ai_conversations")
    op.drop_index(op.f("ix_ai_conversations_agent_key"), table_name="ai_conversations")
    op.drop_index(op.f("ix_ai_conversations_id"), table_name="ai_conversations")
    op.drop_table("ai_conversations")

    op.drop_index(op.f("ix_ai_agent_configs_agent_key"), table_name="ai_agent_configs")
    op.drop_index(op.f("ix_ai_agent_configs_id"), table_name="ai_agent_configs")
    op.drop_table("ai_agent_configs")
