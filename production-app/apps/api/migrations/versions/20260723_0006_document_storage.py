"""add verified object metadata for private documents

Revision ID: 20260723_0006
Revises: 20260723_0005
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260723_0006"
down_revision: str | None = "20260723_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("liquidation_evidence") as batch:
        batch.add_column(sa.Column("content_type", sa.String(120)))
        batch.add_column(sa.Column("size_bytes", sa.Integer()))
        batch.add_column(sa.Column("sha256", sa.String(64)))
        batch.create_index("ix_liquidation_evidence_uploaded_at", ["uploaded_at"])


def downgrade() -> None:
    with op.batch_alter_table("liquidation_evidence") as batch:
        batch.drop_index("ix_liquidation_evidence_uploaded_at")
        batch.drop_column("sha256")
        batch.drop_column("size_bytes")
        batch.drop_column("content_type")
