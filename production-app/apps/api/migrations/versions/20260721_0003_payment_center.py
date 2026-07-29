"""add Additional Budgets and the consolidated DCS payment center

Revision ID: 20260721_0003
Revises: 20260721_0002
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260721_0003"
down_revision: str | None = "20260721_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


budget_kind = sa.Enum("MAIN", "ADDITIONAL", name="budgetkind")
payment_status = sa.Enum(
    "NOT_READY",
    "PENDING",
    "ON_HOLD",
    "PARTIALLY_PAID",
    "PAID",
    "RETURNED",
    name="paymentstatus",
)


def upgrade() -> None:
    bind = op.get_bind()
    budget_kind.create(bind, checkfirst=True)
    payment_status.create(bind, checkfirst=True)

    with op.batch_alter_table("budget_requests") as batch:
        batch.add_column(
            sa.Column("budget_kind", budget_kind, nullable=False, server_default="MAIN")
        )
        batch.add_column(sa.Column("parent_budget_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("additional_reason", sa.Text(), nullable=True))
        batch.add_column(sa.Column("related_expense_description", sa.Text(), nullable=True))
        batch.add_column(sa.Column("related_expense_amount", sa.Numeric(18, 2), nullable=True))
        batch.add_column(
            sa.Column("payment_status", payment_status, nullable=False, server_default="NOT_READY")
        )
        batch.create_foreign_key(
            "fk_budget_requests_parent_budget_id", "budget_requests", ["parent_budget_id"], ["id"]
        )
        batch.create_index("ix_budget_requests_budget_kind", ["budget_kind"])
        batch.create_index("ix_budget_requests_parent_budget_id", ["parent_budget_id"])
        batch.create_index("ix_budget_requests_payment_status", ["payment_status"])

    with op.batch_alter_table("expense_requests") as batch:
        batch.add_column(
            sa.Column("payment_status", payment_status, nullable=False, server_default="NOT_READY")
        )
        batch.create_index("ix_expense_requests_payment_status", ["payment_status"])

    with op.batch_alter_table("releases") as batch:
        batch.add_column(
            sa.Column(
                "source",
                sa.String(length=160),
                nullable=False,
                server_default="Unspecified funding source",
            )
        )
        batch.add_column(
            sa.Column("paid_on", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE"))
        )
        batch.add_column(sa.Column("notes", sa.Text(), nullable=True))

    with op.batch_alter_table("expense_disbursements") as batch:
        batch.add_column(
            sa.Column("paid_on", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE"))
        )
        batch.add_column(sa.Column("notes", sa.Text(), nullable=True))

    op.create_table(
        "payment_annotations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("budget_request_id", sa.String(length=36), nullable=True),
        sa.Column("expense_request_id", sa.String(length=36), nullable=True),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(budget_request_id IS NOT NULL AND expense_request_id IS NULL) OR "
            "(budget_request_id IS NULL AND expense_request_id IS NOT NULL)",
            name="ck_payment_annotation_one_source",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["budget_request_id"], ["budget_requests.id"]),
        sa.ForeignKeyConstraint(["expense_request_id"], ["expense_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payment_annotations_actor_user_id", "payment_annotations", ["actor_user_id"]
    )
    op.create_index(
        "ix_payment_annotations_budget_request_id", "payment_annotations", ["budget_request_id"]
    )
    op.create_index(
        "ix_payment_annotations_expense_request_id", "payment_annotations", ["expense_request_id"]
    )

    # PostgreSQL enum columns require an explicit cast. SQLite stores the same
    # values as text, so PostgreSQL's ``::paymentstatus`` syntax must be omitted
    # for local development and migration smoke tests.
    enum_cast = "::paymentstatus" if op.get_bind().dialect.name == "postgresql" else ""
    op.execute(
        sa.text(
            "UPDATE budget_requests SET payment_status = CASE "
            "WHEN status = 'RELEASED' THEN 'PAID' "
            "WHEN status = 'PARTIALLY_RELEASED' THEN 'PARTIALLY_PAID' "
            f"WHEN status = 'APPROVED' THEN 'PENDING' ELSE 'NOT_READY' END{enum_cast}"
        )
    )
    op.execute(
        sa.text(
            "UPDATE expense_requests SET payment_status = CASE "
            "WHEN status IN ('DISBURSED', 'PENDING_VALIDATION', 'VALIDATED') THEN 'PAID' "
            f"WHEN status = 'APPROVED' THEN 'PENDING' ELSE 'NOT_READY' END{enum_cast}"
        )
    )


def downgrade() -> None:
    op.drop_table("payment_annotations")
    with op.batch_alter_table("expense_disbursements") as batch:
        batch.drop_column("notes")
        batch.drop_column("paid_on")
    with op.batch_alter_table("releases") as batch:
        batch.drop_column("notes")
        batch.drop_column("paid_on")
        batch.drop_column("source")
    with op.batch_alter_table("expense_requests") as batch:
        batch.drop_index("ix_expense_requests_payment_status")
        batch.drop_column("payment_status")
    with op.batch_alter_table("budget_requests") as batch:
        batch.drop_index("ix_budget_requests_payment_status")
        batch.drop_index("ix_budget_requests_parent_budget_id")
        batch.drop_index("ix_budget_requests_budget_kind")
        batch.drop_constraint("fk_budget_requests_parent_budget_id", type_="foreignkey")
        batch.drop_column("payment_status")
        batch.drop_column("related_expense_amount")
        batch.drop_column("related_expense_description")
        batch.drop_column("additional_reason")
        batch.drop_column("parent_budget_id")
        batch.drop_column("budget_kind")
    payment_status.drop(op.get_bind(), checkfirst=True)
    budget_kind.drop(op.get_bind(), checkfirst=True)
