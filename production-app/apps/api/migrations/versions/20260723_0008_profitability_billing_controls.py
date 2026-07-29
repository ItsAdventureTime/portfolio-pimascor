"""add shipment profitability and GM-controlled billing states

Revision ID: 20260723_0008
Revises: 20260723_0007
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260723_0008"
down_revision: str | None = "20260723_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE billingstatus ADD VALUE IF NOT EXISTS 'PENDING_APPROVAL'")
        op.execute("ALTER TYPE billingstatus ADD VALUE IF NOT EXISTS 'APPROVED'")
        op.execute("ALTER TYPE billingstatus ADD VALUE IF NOT EXISTS 'REJECTED'")

    with op.batch_alter_table("billing_records") as batch:
        batch.add_column(sa.Column("submitted_by_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("approved_by_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("rejection_reason", sa.Text(), nullable=True))
        batch.create_foreign_key(
            "fk_billing_records_submitted_by_id_users",
            "users",
            ["submitted_by_id"],
            ["id"],
        )
        batch.create_foreign_key(
            "fk_billing_records_approved_by_id_users",
            "users",
            ["approved_by_id"],
            ["id"],
        )

    with op.batch_alter_table("liquidations") as batch:
        batch.drop_column("journal_posted_at")
        batch.drop_column("journal_reference")

    with op.batch_alter_table("expense_validations") as batch:
        batch.drop_column("journal_reference")


def downgrade() -> None:
    with op.batch_alter_table("expense_validations") as batch:
        batch.add_column(sa.Column("journal_reference", sa.String(160), nullable=True))

    with op.batch_alter_table("liquidations") as batch:
        batch.add_column(sa.Column("journal_reference", sa.String(160), nullable=True))
        batch.add_column(sa.Column("journal_posted_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("billing_records") as batch:
        batch.drop_constraint("fk_billing_records_approved_by_id_users", type_="foreignkey")
        batch.drop_constraint("fk_billing_records_submitted_by_id_users", type_="foreignkey")
        batch.drop_column("rejection_reason")
        batch.drop_column("approved_at")
        batch.drop_column("approved_by_id")
        batch.drop_column("submitted_at")
        batch.drop_column("submitted_by_id")

    # PostgreSQL enum values are intentionally retained because removing enum
    # values is not a safe automatic downgrade.
