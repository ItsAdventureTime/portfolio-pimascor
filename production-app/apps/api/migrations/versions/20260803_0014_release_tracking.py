"""track the latest user-facing release acknowledged per user

Revision ID: 20260803_0014
Revises: 20260803_0013
Create Date: 2026-08-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260803_0014"
down_revision = "20260803_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_seen_release_id", sa.String(length=80), nullable=True))
    op.create_index("ix_users_last_seen_release_id", "users", ["last_seen_release_id"])


def downgrade() -> None:
    op.drop_index("ix_users_last_seen_release_id", table_name="users")
    op.drop_column("users", "last_seen_release_id")
