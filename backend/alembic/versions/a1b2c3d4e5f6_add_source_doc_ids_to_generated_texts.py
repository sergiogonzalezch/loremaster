"""Add source_doc_ids to generated_texts

Revision ID: a1b2c3d4e5f6
Revises: 0e0f6177d0d5
Create Date: 2026-05-16 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "0e0f6177d0d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "generated_texts",
        sa.Column("source_doc_ids", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generated_texts", "source_doc_ids")
