"""add persistent Liquidation, Billing, Collections, and controlled funding

Revision ID: 20260722_0004
Revises: 20260721_0003
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260722_0004"
down_revision: str | None = "20260721_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


classification = postgresql.ENUM(
    "SERVICE_CHARGE", "PASS_THROUGH", name="financialclassification", create_type=False
)
liquidation_status = postgresql.ENUM(
    "DRAFT",
    "SUBMITTED",
    "PENDING_VARIANCE",
    "CLOSED",
    name="liquidationstatus",
    create_type=False,
)
evidence_kind = postgresql.ENUM(
    "RECEIPT",
    "RETURN_PROOF",
    "REIMBURSEMENT_PROOF",
    name="evidencekind",
    create_type=False,
)
billing_status = postgresql.ENUM(
    "DRAFT", "FINALIZED", "VOID", name="billingstatus", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE expensetype ADD VALUE IF NOT EXISTS 'OTHER'")
    classification.create(bind, checkfirst=True)
    liquidation_status.create(bind, checkfirst=True)
    evidence_kind.create(bind, checkfirst=True)
    billing_status.create(bind, checkfirst=True)

    with op.batch_alter_table("budget_request_items") as batch:
        batch.add_column(
            sa.Column(
                "classification",
                classification,
                nullable=False,
                server_default="SERVICE_CHARGE",
            )
        )
    with op.batch_alter_table("expense_requests") as batch:
        batch.alter_column("requested_source", existing_type=sa.String(160), nullable=True)

    op.create_table(
        "funding_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "liquidations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("budget_request_id", sa.String(36), nullable=False),
        sa.Column("requester_id", sa.String(36), nullable=False),
        sa.Column("status", liquidation_status, nullable=False),
        sa.Column("released_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("actual_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("closed_by_id", sa.String(36)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("closure_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["budget_request_id"], ["budget_requests.id"]),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["closed_by_id"], ["users.id"]),
        sa.UniqueConstraint("budget_request_id", name="uq_liquidation_budget"),
    )
    op.create_index("ix_liquidations_budget_request_id", "liquidations", ["budget_request_id"])
    op.create_index("ix_liquidations_requester_id", "liquidations", ["requester_id"])
    op.create_index("ix_liquidations_status", "liquidations", ["status"])

    op.create_table(
        "liquidation_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("liquidation_id", sa.String(36), nullable=False),
        sa.Column("description", sa.String(240), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["liquidation_id"], ["liquidations.id"]),
    )
    op.create_index("ix_liquidation_lines_liquidation_id", "liquidation_lines", ["liquidation_id"])

    op.create_table(
        "liquidation_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("liquidation_id", sa.String(36), nullable=False),
        sa.Column("kind", evidence_kind, nullable=False),
        sa.Column("file_name", sa.String(240), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("uploaded_by_id", sa.String(36), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["liquidation_id"], ["liquidations.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
    )
    op.create_index("ix_liquidation_evidence_liquidation_id", "liquidation_evidence", ["liquidation_id"])

    op.create_table(
        "billing_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("reference", sa.String(60), nullable=False, unique=True),
        sa.Column("budget_request_id", sa.String(36), nullable=False),
        sa.Column("replaces_billing_id", sa.String(36)),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("service_subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("pass_through_subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("vat_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("withholding_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("net_due", sa.Numeric(18, 2), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("status", billing_status, nullable=False),
        sa.Column("prepared_by_id", sa.String(36), nullable=False),
        sa.Column("finalized_by_id", sa.String(36)),
        sa.Column("finalized_at", sa.DateTime(timezone=True)),
        sa.Column("voided_by_id", sa.String(36)),
        sa.Column("voided_at", sa.DateTime(timezone=True)),
        sa.Column("void_reason", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["budget_request_id"], ["budget_requests.id"]),
        sa.ForeignKeyConstraint(["replaces_billing_id"], ["billing_records.id"]),
        sa.ForeignKeyConstraint(["prepared_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["finalized_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["voided_by_id"], ["users.id"]),
    )
    op.create_index("ix_billing_records_reference", "billing_records", ["reference"])
    op.create_index("ix_billing_records_budget_request_id", "billing_records", ["budget_request_id"])
    op.create_index("ix_billing_records_status", "billing_records", ["status"])

    op.create_table(
        "billing_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("billing_id", sa.String(36), nullable=False),
        sa.Column("description", sa.String(240), nullable=False),
        sa.Column("classification", classification, nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["billing_id"], ["billing_records.id"]),
    )
    op.create_index("ix_billing_lines_billing_id", "billing_lines", ["billing_id"])

    op.create_table(
        "client_payments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("reference", sa.String(60), nullable=False, unique=True),
        sa.Column("client_id", sa.String(36), nullable=False),
        sa.Column("payment_reference", sa.String(160), nullable=False, unique=True),
        sa.Column("receiving_bank", sa.String(160), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("recorded_by_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["recorded_by_id"], ["users.id"]),
    )
    op.create_index("ix_client_payments_reference", "client_payments", ["reference"])
    op.create_index("ix_client_payments_client_id", "client_payments", ["client_id"])

    op.create_table(
        "payment_allocations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("payment_id", sa.String(36), nullable=False),
        sa.Column("billing_id", sa.String(36), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["client_payments.id"]),
        sa.ForeignKeyConstraint(["billing_id"], ["billing_records.id"]),
        sa.UniqueConstraint("payment_id", "billing_id", name="uq_payment_billing_allocation"),
    )
    op.create_index("ix_payment_allocations_payment_id", "payment_allocations", ["payment_id"])
    op.create_index("ix_payment_allocations_billing_id", "payment_allocations", ["billing_id"])


def downgrade() -> None:
    op.drop_table("payment_allocations")
    op.drop_table("client_payments")
    op.drop_table("billing_lines")
    op.drop_table("billing_records")
    op.drop_table("liquidation_evidence")
    op.drop_table("liquidation_lines")
    op.drop_table("liquidations")
    op.drop_table("funding_sources")
    with op.batch_alter_table("expense_requests") as batch:
        batch.alter_column("requested_source", existing_type=sa.String(160), nullable=False)
    with op.batch_alter_table("budget_request_items") as batch:
        batch.drop_column("classification")
    billing_status.drop(op.get_bind(), checkfirst=True)
    evidence_kind.drop(op.get_bind(), checkfirst=True)
    liquidation_status.drop(op.get_bind(), checkfirst=True)
    classification.drop(op.get_bind(), checkfirst=True)
    # PostgreSQL enum values cannot be removed safely in-place. OTHER remains
    # available after downgrade; removing it needs a separately reviewed enum
    # replacement after confirming that no rows use the value.
