"""add privacy-minimized incident reporting

Revision ID: 20260723_0007
Revises: 20260723_0006
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260723_0007"
down_revision: str | None = "20260723_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


incident_source = sa.Enum("CLIENT", "SERVER", name="incidentsource")
incident_severity = sa.Enum("RECOVERABLE", "BLOCKING", name="incidentseverity")
incident_status = sa.Enum(
    "REPORTED", "DISMISSED", "CLOSED_BY_USER", name="incidentstatus"
)
incident_decision = sa.Enum(
    "CONTINUED", "STOPPED", "DISMISSED", name="incidentdecision"
)


def upgrade() -> None:
    op.create_table(
        "incident_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_report_id", sa.String(36), nullable=True),
        sa.Column("reference", sa.String(40), nullable=False),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("source", incident_source, nullable=False),
        sa.Column("severity", incident_severity, nullable=False),
        sa.Column("status", incident_status, nullable=False),
        sa.Column("operation", sa.String(160), nullable=False),
        sa.Column("user_action", sa.Text(), nullable=False),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("recovery_suggestion", sa.Text(), nullable=False),
        sa.Column("can_continue", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("page_path", sa.String(240), nullable=False),
        sa.Column("request_method", sa.String(12), nullable=True),
        sa.Column("request_path", sa.String(240), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=False),
        sa.Column("technical_summary", sa.Text(), nullable=True),
        sa.Column("client_runtime", sa.String(80), nullable=True),
        sa.Column("deployment_tier", sa.String(20), nullable=False),
        sa.Column("correlation_id", sa.String(36), nullable=True),
        sa.Column("email_admin_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_developer_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision", incident_decision, nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incident_reports_client_report_id", "incident_reports", ["client_report_id"], unique=True)
    op.create_index("ix_incident_reports_reference", "incident_reports", ["reference"], unique=True)
    op.create_index("ix_incident_reports_actor_user_id", "incident_reports", ["actor_user_id"])
    op.create_index("ix_incident_reports_source", "incident_reports", ["source"])
    op.create_index("ix_incident_reports_severity", "incident_reports", ["severity"])
    op.create_index("ix_incident_reports_status", "incident_reports", ["status"])
    op.create_index("ix_incident_reports_error_code", "incident_reports", ["error_code"])
    op.create_index("ix_incident_reports_correlation_id", "incident_reports", ["correlation_id"])
    op.create_index("ix_incident_reports_created_at", "incident_reports", ["created_at"])


def downgrade() -> None:
    op.drop_table("incident_reports")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        incident_decision.drop(bind, checkfirst=True)
        incident_status.drop(bind, checkfirst=True)
        incident_severity.drop(bind, checkfirst=True)
        incident_source.drop(bind, checkfirst=True)
