"""add durable local records export requests

Revision ID: 20260729_0011
Revises: 20260729_0010
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260729_0011"
down_revision = "20260729_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    status = sa.Enum("QUEUED", "PROCESSING", "READY", "EXPIRED", "FAILED", name="dataexportstatus")
    status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "data_exports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("requested_by_id", sa.String(length=36), nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("storage_key", sa.String(length=500), nullable=True),
        sa.Column("file_name", sa.String(length=240), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_exports_requested_by_id", "data_exports", ["requested_by_id"])
    op.create_index("ix_data_exports_status", "data_exports", ["status"])
    op.create_index("ix_data_exports_requested_at", "data_exports", ["requested_at"])
    op.create_index("ix_data_exports_expires_at", "data_exports", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_data_exports_expires_at", table_name="data_exports")
    op.drop_index("ix_data_exports_requested_at", table_name="data_exports")
    op.drop_index("ix_data_exports_status", table_name="data_exports")
    op.drop_index("ix_data_exports_requested_by_id", table_name="data_exports")
    op.drop_table("data_exports")
    sa.Enum(name="dataexportstatus").drop(op.get_bind(), checkfirst=True)
