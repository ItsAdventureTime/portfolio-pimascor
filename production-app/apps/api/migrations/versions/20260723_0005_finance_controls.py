"""add configured tax, invoice detail, credit memo, and check controls

Revision ID: 20260723_0005
Revises: 20260722_0004
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260723_0005"
down_revision: str | None = "20260722_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


classification = postgresql.ENUM(
    "SERVICE_CHARGE", "PASS_THROUGH", name="financialclassification", create_type=False
)
credit_memo_status = postgresql.ENUM(
    "DRAFT", "PENDING_APPROVAL", "APPROVED", "REJECTED",
    name="creditmemostatus", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    credit_memo_status.create(bind, checkfirst=True)

    with op.batch_alter_table("budget_requests") as batch:
        batch.add_column(sa.Column("notes", sa.Text()))

    with op.batch_alter_table("liquidations") as batch:
        batch.add_column(sa.Column("journal_reference", sa.String(160)))
        batch.add_column(sa.Column("journal_posted_at", sa.DateTime(timezone=True)))

    with op.batch_alter_table("billing_records") as batch:
        batch.add_column(sa.Column("client_address", sa.Text()))
        batch.add_column(sa.Column("category", sa.String(120)))
        batch.add_column(sa.Column("shipper_consignee", sa.String(240)))
        batch.add_column(sa.Column("container_number", sa.String(120)))
        batch.add_column(sa.Column("destination", sa.String(160)))
        batch.add_column(sa.Column("vessel", sa.String(160)))
        batch.add_column(sa.Column("bl_awb_number", sa.String(160)))
        batch.add_column(sa.Column("exchange_rate", sa.Numeric(18, 6)))
        batch.add_column(sa.Column("measurement", sa.String(120)))

    with op.batch_alter_table("billing_lines") as batch:
        batch.add_column(sa.Column("vat_rate", sa.Numeric(7, 6), nullable=False, server_default="0"))
        batch.add_column(sa.Column("withholding_rate", sa.Numeric(7, 6), nullable=False, server_default="0"))
        batch.add_column(sa.Column("vat_amount", sa.Numeric(18, 2), nullable=False, server_default="0"))
        batch.add_column(sa.Column("withholding_amount", sa.Numeric(18, 2), nullable=False, server_default="0"))

    with op.batch_alter_table("client_payments") as batch:
        batch.add_column(sa.Column("payment_method", sa.String(40), nullable=False, server_default="CHECK"))
        batch.add_column(sa.Column("check_number", sa.String(120)))
        batch.add_column(sa.Column("check_list_number", sa.String(120)))
        batch.create_index("ix_client_payments_check_number", ["check_number"])

    op.create_table(
        "tax_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False, unique=True),
        sa.Column("classification", classification, nullable=False),
        sa.Column("vat_rate", sa.Numeric(7, 6), nullable=False),
        sa.Column("withholding_rate", sa.Numeric(7, 6), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tax_profiles_classification", "tax_profiles", ["classification"])

    op.create_table(
        "credit_memos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("reference", sa.String(60), nullable=False, unique=True),
        sa.Column("billing_id", sa.String(36), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", credit_memo_status, nullable=False),
        sa.Column("created_by_id", sa.String(36), nullable=False),
        sa.Column("approved_by_id", sa.String(36)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["billing_id"], ["billing_records.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"]),
    )
    op.create_index("ix_credit_memos_reference", "credit_memos", ["reference"])
    op.create_index("ix_credit_memos_billing_id", "credit_memos", ["billing_id"])
    op.create_index("ix_credit_memos_status", "credit_memos", ["status"])


def downgrade() -> None:
    op.drop_table("credit_memos")
    op.drop_table("tax_profiles")
    with op.batch_alter_table("client_payments") as batch:
        batch.drop_index("ix_client_payments_check_number")
        batch.drop_column("check_list_number")
        batch.drop_column("check_number")
        batch.drop_column("payment_method")
    with op.batch_alter_table("billing_lines") as batch:
        batch.drop_column("withholding_amount")
        batch.drop_column("vat_amount")
        batch.drop_column("withholding_rate")
        batch.drop_column("vat_rate")
    with op.batch_alter_table("billing_records") as batch:
        for column in (
            "measurement", "exchange_rate", "bl_awb_number", "vessel", "destination",
            "container_number", "shipper_consignee", "category", "client_address",
        ):
            batch.drop_column(column)
    with op.batch_alter_table("liquidations") as batch:
        batch.drop_column("journal_posted_at")
        batch.drop_column("journal_reference")
    with op.batch_alter_table("budget_requests") as batch:
        batch.drop_column("notes")
    credit_memo_status.drop(op.get_bind(), checkfirst=True)
