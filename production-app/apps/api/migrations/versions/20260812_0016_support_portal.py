"""add secure support portals, Markdown metadata, and attachments

Revision ID: 20260812_0016
Revises: 20260812_0015
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260812_0016"
down_revision: str | None = "20260812_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "support_tickets",
        sa.Column("category", sa.String(80), nullable=False, server_default="OTHER"),
    )
    op.add_column(
        "support_tickets",
        sa.Column("reason", sa.String(160), nullable=False, server_default="OTHER"),
    )
    op.add_column("support_tickets", sa.Column("assigned_to_key", sa.String(40), nullable=True))
    op.add_column("support_tickets", sa.Column("closure_reason", sa.String(80), nullable=True))
    op.create_index("ix_support_tickets_assigned_to_key", "support_tickets", ["assigned_to_key"])
    op.alter_column("support_tickets", "category", server_default=None)
    op.alter_column("support_tickets", "reason", server_default=None)

    op.add_column("support_ticket_replies", sa.Column("author_label", sa.String(80), nullable=True))
    op.alter_column("support_ticket_replies", "author_user_id", nullable=True)

    op.create_table(
        "support_ticket_portal_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticket_id", sa.String(36), sa.ForeignKey("support_tickets.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("audience", sa.String(20), nullable=False),
        sa.Column("recipient_key", sa.String(40), nullable=False),
        sa.Column("recipient_email", sa.String(320), nullable=False),
        sa.Column("recipient_label", sa.String(80), nullable=False),
        sa.Column("recipient_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_support_ticket_portal_tokens_ticket_id",
        "support_ticket_portal_tokens",
        ["ticket_id"],
    )
    op.create_index(
        "ix_support_ticket_portal_tokens_token_hash",
        "support_ticket_portal_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_support_ticket_portal_tokens_audience",
        "support_ticket_portal_tokens",
        ["audience"],
    )
    op.create_index(
        "ix_support_ticket_portal_tokens_recipient_key",
        "support_ticket_portal_tokens",
        ["recipient_key"],
    )
    op.create_index(
        "ix_support_ticket_portal_tokens_recipient_user_id",
        "support_ticket_portal_tokens",
        ["recipient_user_id"],
    )
    op.create_index(
        "ix_support_ticket_portal_tokens_expires_at",
        "support_ticket_portal_tokens",
        ["expires_at"],
    )

    op.create_table(
        "support_ticket_attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticket_id", sa.String(36), sa.ForeignKey("support_tickets.id"), nullable=False),
        sa.Column("reply_id", sa.String(36), sa.ForeignKey("support_ticket_replies.id"), nullable=True),
        sa.Column("uploaded_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("uploaded_by_label", sa.String(80), nullable=False),
        sa.Column("file_name", sa.String(240), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("simulated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_support_ticket_attachments_ticket_id",
        "support_ticket_attachments",
        ["ticket_id"],
    )
    op.create_index(
        "ix_support_ticket_attachments_reply_id",
        "support_ticket_attachments",
        ["reply_id"],
    )
    op.create_index(
        "ix_support_ticket_attachments_uploaded_by_user_id",
        "support_ticket_attachments",
        ["uploaded_by_user_id"],
    )
    op.create_index(
        "ix_support_ticket_attachments_created_at",
        "support_ticket_attachments",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("support_ticket_attachments")
    op.drop_table("support_ticket_portal_tokens")
    op.alter_column("support_ticket_replies", "author_user_id", nullable=False)
    op.drop_column("support_ticket_replies", "author_label")
    op.drop_index("ix_support_tickets_assigned_to_key", table_name="support_tickets")
    op.drop_column("support_tickets", "closure_reason")
    op.drop_column("support_tickets", "assigned_to_key")
    op.drop_column("support_tickets", "reason")
    op.drop_column("support_tickets", "category")
