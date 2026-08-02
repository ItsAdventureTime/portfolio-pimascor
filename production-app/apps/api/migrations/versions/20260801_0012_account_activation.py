"""add first-login account activation state

Revision ID: 20260801_0012
Revises: 20260729_0011
Create Date: 2026-08-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260801_0012"
down_revision = "20260729_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("must_set_password", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # SQLite cannot execute ALTER COLUMN ... DROP DEFAULT. Its metadata
    # default is harmless for tests and fresh local databases; PostgreSQL
    # removes the migration-only default after backfilling the column.
    if op.get_bind().dialect.name != "sqlite":
        op.alter_column("users", "must_set_password", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "must_set_password")
