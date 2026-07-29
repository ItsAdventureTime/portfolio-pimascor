"""Initial application schema.

Revision ID: 20260720_0001
Revises:
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260720_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


user_status = sa.Enum("ACTIVE", "DISABLED", name="userstatus")
role = sa.Enum("ADMIN", "REQUESTER", "GM", "DCS", "MICH", name="role")
budget_status = sa.Enum(
    "DRAFT",
    "PENDING_APPROVAL",
    "APPROVED",
    "REJECTED",
    "PARTIALLY_RELEASED",
    "RELEASED",
    "CANCELLED",
    name="budgetstatus",
)
item_kind = sa.Enum("BUYING", "SELLING", name="itemkind")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("role", role, nullable=False),
        sa.Column("status", user_status, nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "clients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    op.create_table(
        "email_challenges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("code_hash", sa.String(length=512), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_challenges_expires_at", "email_challenges", ["expires_at"])
    op.create_index("ix_email_challenges_user_id", "email_challenges", ["user_id"])

    op.create_table(
        "budget_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("reference", sa.String(length=40), nullable=False),
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("shipment_reference", sa.String(length=120), nullable=False),
        sa.Column("request_date", sa.Date(), nullable=False),
        sa.Column("requester_id", sa.String(length=36), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("buying_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("selling_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("released_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", budget_status, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_budget_requests_client_id", "budget_requests", ["client_id"])
    op.create_index("ix_budget_requests_reference", "budget_requests", ["reference"], unique=True)
    op.create_index("ix_budget_requests_requester_id", "budget_requests", ["requester_id"])

    op.create_table(
        "budget_request_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("budget_request_id", sa.String(length=36), nullable=False),
        sa.Column("kind", item_kind, nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["budget_request_id"], ["budget_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_budget_request_items_budget_request_id", "budget_request_items", ["budget_request_id"])

    op.create_table(
        "budget_submissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("budget_request_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("submitted_by_id", sa.String(length=36), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["budget_request_id"], ["budget_requests.id"]),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("budget_request_id", "version", name="uq_submission_version"),
    )
    op.create_index("ix_budget_submissions_budget_request_id", "budget_submissions", ["budget_request_id"])

    op.create_table(
        "approval_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["submission_id"], ["budget_submissions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_decisions_submission_id", "approval_decisions", ["submission_id"])

    op.create_table(
        "releases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("budget_request_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("mode", sa.String(length=40), nullable=False),
        sa.Column("recipient", sa.String(length=160), nullable=False),
        sa.Column("transaction_reference", sa.String(length=120), nullable=False),
        sa.Column("released_by_id", sa.String(length=36), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["budget_request_id"], ["budget_requests.id"]),
        sa.ForeignKeyConstraint(["released_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_reference"),
    )
    op.create_index("ix_releases_budget_request_id", "releases", ["budget_request_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(length=36), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])
    op.create_index("ix_audit_events_correlation_id", "audit_events", ["correlation_id"])
    op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"])
    op.create_index("ix_audit_events_entity_type", "audit_events", ["entity_type"])
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("releases")
    op.drop_table("approval_decisions")
    op.drop_table("budget_submissions")
    op.drop_table("budget_request_items")
    op.drop_table("budget_requests")
    op.drop_table("email_challenges")
    op.drop_table("sessions")
    op.drop_table("clients")
    op.drop_table("users")
    item_kind.drop(op.get_bind(), checkfirst=True)
    budget_status.drop(op.get_bind(), checkfirst=True)
    role.drop(op.get_bind(), checkfirst=True)
    user_status.drop(op.get_bind(), checkfirst=True)
