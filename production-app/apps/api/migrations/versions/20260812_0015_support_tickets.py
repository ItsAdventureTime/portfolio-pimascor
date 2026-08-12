"""add durable support tickets and append-only replies

Revision ID: 20260812_0015
Revises: 20260803_0014
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260812_0015"
down_revision: str | None = "20260803_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


support_ticket_status = sa.Enum(
    "OPEN",
    "IN_PROGRESS",
    "WAITING_FOR_REQUESTER",
    "RESOLVED",
    "CLOSED",
    name="supportticketstatus",
)
role = sa.Enum(
    "ADMIN",
    "REQUESTER",
    "GM",
    "DCS",
    "MICH",
    name="role",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticket_number", sa.String(40), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("requester_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("requester_role", role, nullable=False),
        sa.Column("deployment_tier", sa.String(20), nullable=False),
        sa.Column("status", support_ticket_status, nullable=False),
        sa.Column("assigned_to_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_admin_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_developer_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_support_tickets_ticket_number", "support_tickets", ["ticket_number"], unique=True)
    op.create_index("ix_support_tickets_requester_id", "support_tickets", ["requester_id"])
    op.create_index("ix_support_tickets_requester_role", "support_tickets", ["requester_role"])
    op.create_index("ix_support_tickets_deployment_tier", "support_tickets", ["deployment_tier"])
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])
    op.create_index("ix_support_tickets_assigned_to_id", "support_tickets", ["assigned_to_id"])
    op.create_index("ix_support_tickets_created_at", "support_tickets", ["created_at"])

    op.create_table(
        "support_ticket_replies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.String(36),
            sa.ForeignKey("support_tickets.id"),
            nullable=False,
        ),
        sa.Column("author_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("author_role", role, nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("email_admin_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_developer_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_support_ticket_replies_ticket_id", "support_ticket_replies", ["ticket_id"])
    op.create_index(
        "ix_support_ticket_replies_author_user_id",
        "support_ticket_replies",
        ["author_user_id"],
    )
    op.create_index("ix_support_ticket_replies_author_role", "support_ticket_replies", ["author_role"])
    op.create_index("ix_support_ticket_replies_created_at", "support_ticket_replies", ["created_at"])


def downgrade() -> None:
    op.drop_table("support_ticket_replies")
    op.drop_table("support_tickets")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        support_ticket_status.drop(bind, checkfirst=True)
