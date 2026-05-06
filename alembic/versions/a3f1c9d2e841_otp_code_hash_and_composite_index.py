"""otp_code_hash_and_composite_index

Revision ID: a3f1c9d2e841
Revises: 65c72853a0e7
Create Date: 2026-05-06

Changes:
- Widen otp_codes.code from VARCHAR(6) to VARCHAR(64) to hold SHA-256 hex digests.
- Add composite index ix_otp_email_purpose_used on (email, purpose, is_used).
"""
from alembic import op
import sqlalchemy as sa

revision = "a3f1c9d2e841"
down_revision = "65c72853a0e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Widen the code column to store a 64-character SHA-256 hex digest.
    op.alter_column(
        "otp_codes",
        "code",
        existing_type=sa.String(length=6),
        type_=sa.String(length=64),
        nullable=False,
    )
    # Add composite index used by OTP lookup queries.
    op.create_index(
        "ix_otp_email_purpose_used",
        "otp_codes",
        ["email", "purpose", "is_used"],
    )


def downgrade() -> None:
    op.drop_index("ix_otp_email_purpose_used", table_name="otp_codes")
    op.alter_column(
        "otp_codes",
        "code",
        existing_type=sa.String(length=64),
        type_=sa.String(length=6),
        nullable=False,
    )
