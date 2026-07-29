"""add owner-meeting workflow controls

Revision ID: 20260724_0009
Revises: 20260723_0008
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260724_0009"
down_revision: str | None = "20260723_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE budgetstatus ADD VALUE IF NOT EXISTS 'PENDING_REVIEW'")
        op.execute("ALTER TYPE evidencekind ADD VALUE IF NOT EXISTS 'PHYSICAL_RECEIPTS_PHOTO'")

    status_values = (
        "DRAFT",
        "PENDING_APPROVAL",
        "APPROVED",
        "REJECTED",
        "CLIENT_ACCEPTED",
    )
    if bind.dialect.name == "postgresql":
        postgresql.ENUM(*status_values, name="quotationstatus").create(bind, checkfirst=True)
        quotation_status = postgresql.ENUM(
            *status_values,
            name="quotationstatus",
            create_type=False,
        )
    else:
        quotation_status = sa.Enum(*status_values, name="quotationstatus")
    op.create_table(
        "sales_quotations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("reference", sa.String(60), nullable=False),
        sa.Column("client_id", sa.String(36), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("shipment_reference", sa.String(120), nullable=False),
        sa.Column("quoted_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("terms_and_conditions", sa.Text(), nullable=False),
        sa.Column("status", quotation_status, nullable=False),
        sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("approved_by_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("decision_reason", sa.Text()),
        sa.Column("client_accepted_at", sa.Date()),
        sa.Column("client_signatory", sa.String(200)),
        sa.Column("signed_file_name", sa.String(240)),
        sa.Column("signed_storage_key", sa.String(500)),
        sa.Column("signed_content_type", sa.String(120)),
        sa.Column("signed_size_bytes", sa.Integer()),
        sa.Column("signed_sha256", sa.String(64)),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sales_quotations_reference", "sales_quotations", ["reference"], unique=True)
    op.create_index("ix_sales_quotations_client_id", "sales_quotations", ["client_id"])
    op.create_index("ix_sales_quotations_shipment_reference", "sales_quotations", ["shipment_reference"])
    op.create_index("ix_sales_quotations_status", "sales_quotations", ["status"])
    op.create_index("ix_sales_quotations_created_by_id", "sales_quotations", ["created_by_id"])

    with op.batch_alter_table("budget_requests") as batch:
        batch.add_column(sa.Column("quotation_id", sa.String(36), nullable=True))
        batch.create_index("ix_budget_requests_quotation_id", ["quotation_id"])
        batch.create_foreign_key(
            "fk_budget_requests_quotation_id_sales_quotations",
            "sales_quotations",
            ["quotation_id"],
            ["id"],
        )
        batch.add_column(sa.Column("reviewed_by_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("review_note", sa.Text(), nullable=True))
        batch.create_index("ix_budget_requests_reviewed_by_id", ["reviewed_by_id"])
        batch.create_foreign_key(
            "fk_budget_requests_reviewed_by_id_users",
            "users",
            ["reviewed_by_id"],
            ["id"],
        )

    with op.batch_alter_table("liquidations") as batch:
        batch.add_column(
            sa.Column(
                "originals_received_confirmed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch.add_column(sa.Column("originals_received_at", sa.DateTime(timezone=True), nullable=True))

    for table in ("releases", "expense_disbursements"):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("proof_file_name", sa.String(240), nullable=True))
            batch.add_column(sa.Column("proof_storage_key", sa.String(500), nullable=True))
            batch.add_column(sa.Column("proof_content_type", sa.String(120), nullable=True))
            batch.add_column(sa.Column("proof_size_bytes", sa.Integer(), nullable=True))
            batch.add_column(sa.Column("proof_sha256", sa.String(64), nullable=True))


def downgrade() -> None:
    for table in ("expense_disbursements", "releases"):
        with op.batch_alter_table(table) as batch:
            batch.drop_column("proof_sha256")
            batch.drop_column("proof_size_bytes")
            batch.drop_column("proof_content_type")
            batch.drop_column("proof_storage_key")
            batch.drop_column("proof_file_name")

    with op.batch_alter_table("liquidations") as batch:
        batch.drop_column("originals_received_at")
        batch.drop_column("originals_received_confirmed")

    with op.batch_alter_table("budget_requests") as batch:
        batch.drop_constraint("fk_budget_requests_quotation_id_sales_quotations", type_="foreignkey")
        batch.drop_index("ix_budget_requests_quotation_id")
        batch.drop_column("quotation_id")
        batch.drop_constraint("fk_budget_requests_reviewed_by_id_users", type_="foreignkey")
        batch.drop_index("ix_budget_requests_reviewed_by_id")
        batch.drop_column("review_note")
        batch.drop_column("reviewed_at")
        batch.drop_column("reviewed_by_id")

    op.drop_index("ix_sales_quotations_created_by_id", table_name="sales_quotations")
    op.drop_index("ix_sales_quotations_status", table_name="sales_quotations")
    op.drop_index("ix_sales_quotations_shipment_reference", table_name="sales_quotations")
    op.drop_index("ix_sales_quotations_client_id", table_name="sales_quotations")
    op.drop_index("ix_sales_quotations_reference", table_name="sales_quotations")
    op.drop_table("sales_quotations")
    if op.get_bind().dialect.name == "postgresql":
        postgresql.ENUM(name="quotationstatus").drop(op.get_bind(), checkfirst=True)
