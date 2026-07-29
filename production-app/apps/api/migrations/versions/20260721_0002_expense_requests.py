"""add OPEX, Marketing, and Loan Payment workflows

Revision ID: 20260721_0002
Revises: 20260720_0001
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260721_0002"
down_revision: str | None = "20260720_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


expense_type = sa.Enum("OPEX", "MARKETING", "LOAN_PAYMENT", name="expensetype")
expense_status = sa.Enum(
    "DRAFT",
    "PENDING_APPROVAL",
    "APPROVED",
    "REJECTED",
    "DISBURSED",
    "PENDING_VALIDATION",
    "VALIDATED",
    "CANCELLED",
    name="expensestatus",
)


def upgrade() -> None:
    op.create_table(
        "expense_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("reference", sa.String(length=40), nullable=False),
        sa.Column("expense_type", expense_type, nullable=False),
        sa.Column("requester_id", sa.String(length=36), nullable=False),
        sa.Column("request_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("party", sa.String(length=200), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("requested_source", sa.String(length=160), nullable=False),
        sa.Column("loan_reference", sa.String(length=160), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("principal_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("interest_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("penalties_fees_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", expense_status, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_expense_amount_positive"),
        sa.CheckConstraint("principal_amount >= 0", name="ck_expense_principal_nonnegative"),
        sa.CheckConstraint("interest_amount >= 0", name="ck_expense_interest_nonnegative"),
        sa.CheckConstraint("penalties_fees_amount >= 0", name="ck_expense_fees_nonnegative"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index("ix_expense_requests_reference", "expense_requests", ["reference"])
    op.create_index("ix_expense_requests_expense_type", "expense_requests", ["expense_type"])
    op.create_index("ix_expense_requests_requester_id", "expense_requests", ["requester_id"])
    op.create_index("ix_expense_requests_status", "expense_requests", ["status"])

    op.create_table(
        "expense_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("expense_request_id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["expense_request_id"], ["expense_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expense_decisions_actor_user_id", "expense_decisions", ["actor_user_id"])
    op.create_index("ix_expense_decisions_expense_request_id", "expense_decisions", ["expense_request_id"])

    op.create_table(
        "expense_disbursements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("expense_request_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("mode", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=160), nullable=False),
        sa.Column("paid_to", sa.String(length=200), nullable=False),
        sa.Column("transaction_reference", sa.String(length=160), nullable=False),
        sa.Column("disbursed_by_id", sa.String(length=36), nullable=False),
        sa.Column("disbursed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["disbursed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["expense_request_id"], ["expense_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("expense_request_id", name="uq_expense_disbursement_request"),
        sa.UniqueConstraint("transaction_reference"),
    )
    op.create_index("ix_expense_disbursements_disbursed_by_id", "expense_disbursements", ["disbursed_by_id"])
    op.create_index("ix_expense_disbursements_expense_request_id", "expense_disbursements", ["expense_request_id"])

    op.create_table(
        "expense_validations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("expense_request_id", sa.String(length=36), nullable=False),
        sa.Column("validated_by_id", sa.String(length=36), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("journal_reference", sa.String(length=160), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["expense_request_id"], ["expense_requests.id"]),
        sa.ForeignKeyConstraint(["validated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("expense_request_id", name="uq_expense_validation_request"),
    )
    op.create_index("ix_expense_validations_expense_request_id", "expense_validations", ["expense_request_id"])
    op.create_index("ix_expense_validations_validated_by_id", "expense_validations", ["validated_by_id"])


def downgrade() -> None:
    op.drop_index("ix_expense_validations_validated_by_id", table_name="expense_validations")
    op.drop_index("ix_expense_validations_expense_request_id", table_name="expense_validations")
    op.drop_table("expense_validations")
    op.drop_index("ix_expense_disbursements_expense_request_id", table_name="expense_disbursements")
    op.drop_index("ix_expense_disbursements_disbursed_by_id", table_name="expense_disbursements")
    op.drop_table("expense_disbursements")
    op.drop_index("ix_expense_decisions_expense_request_id", table_name="expense_decisions")
    op.drop_index("ix_expense_decisions_actor_user_id", table_name="expense_decisions")
    op.drop_table("expense_decisions")
    op.drop_index("ix_expense_requests_status", table_name="expense_requests")
    op.drop_index("ix_expense_requests_requester_id", table_name="expense_requests")
    op.drop_index("ix_expense_requests_expense_type", table_name="expense_requests")
    op.drop_index("ix_expense_requests_reference", table_name="expense_requests")
    op.drop_table("expense_requests")
    expense_status.drop(op.get_bind(), checkfirst=True)
    expense_type.drop(op.get_bind(), checkfirst=True)
