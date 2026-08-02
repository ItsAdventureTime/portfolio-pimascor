"""add self-service password reset request ledger

Revision ID: 20260803_0013
Revises: 20260801_0012
Create Date: 2026-08-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260803_0013"
down_revision = "20260801_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("identifier_hash", sa.String(length=64), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_password_reset_requests_user_id", "password_reset_requests", ["user_id"])
    op.create_index("ix_password_reset_requests_identifier_hash", "password_reset_requests", ["identifier_hash"])
    op.create_index("ix_password_reset_requests_source_hash", "password_reset_requests", ["source_hash"])
    op.create_index("ix_password_reset_requests_expires_at", "password_reset_requests", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_requests_expires_at", table_name="password_reset_requests")
    op.drop_index("ix_password_reset_requests_source_hash", table_name="password_reset_requests")
    op.drop_index("ix_password_reset_requests_identifier_hash", table_name="password_reset_requests")
    op.drop_index("ix_password_reset_requests_user_id", table_name="password_reset_requests")
    op.drop_table("password_reset_requests")
