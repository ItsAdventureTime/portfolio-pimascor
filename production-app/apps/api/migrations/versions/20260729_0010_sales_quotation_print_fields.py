"""add sales quotation print fields and dual-currency lines

Revision ID: 20260729_0010
Revises: 20260724_0009
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260729_0010"
down_revision: str | None = "20260724_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("sales_quotations") as batch:
        batch.add_column(sa.Column("mode_of_transport", sa.String(40)))
        batch.add_column(sa.Column("container_type", sa.String(40)))
        batch.add_column(sa.Column("origin", sa.String(160)))
        batch.add_column(sa.Column("destination", sa.String(160)))
        batch.add_column(sa.Column("incoterms", sa.String(40)))
        batch.add_column(sa.Column("cargo_details", sa.String(500)))
        batch.add_column(sa.Column("payment_terms", sa.String(500)))
        batch.add_column(sa.Column("validity_hours", sa.Integer(), nullable=False, server_default="48"))

    op.create_table(
        "sales_quotation_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("quotation_id", sa.String(36), sa.ForeignKey("sales_quotations.id"), nullable=False),
        sa.Column("section", sa.String(40), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("billed_by", sa.String(30), nullable=False, server_default="PIMASCOR"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_sales_quotation_lines_quotation_id", "sales_quotation_lines", ["quotation_id"])


def downgrade() -> None:
    op.drop_index("ix_sales_quotation_lines_quotation_id", table_name="sales_quotation_lines")
    op.drop_table("sales_quotation_lines")
    with op.batch_alter_table("sales_quotations") as batch:
        batch.drop_column("validity_hours")
        batch.drop_column("payment_terms")
        batch.drop_column("cargo_details")
        batch.drop_column("incoterms")
        batch.drop_column("destination")
        batch.drop_column("origin")
        batch.drop_column("container_type")
        batch.drop_column("mode_of_transport")
