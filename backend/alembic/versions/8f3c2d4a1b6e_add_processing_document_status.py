"""Add processing value to documentstatus enum

Revision ID: 8f3c2d4a1b6e
Revises: 75730f468081
Create Date: 2026-04-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f3c2d4a1b6e"
down_revision: Union[str, Sequence[str], None] = "75730f468081"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE documentstatus ADD VALUE IF NOT EXISTS 'processing'")
    else:
        with op.batch_alter_table("documents", schema=None) as batch_op:
            batch_op.alter_column(
                "status",
                existing_type=sa.Enum("completed", "failed", name="documentstatus"),
                type_=sa.Enum(
                    "processing", "completed", "failed", name="documentstatus"
                ),
                existing_nullable=False,
            )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("UPDATE documents SET status = 'completed' WHERE status = 'processing'")
        op.execute("ALTER TYPE documentstatus RENAME TO documentstatus_old")
        op.execute("CREATE TYPE documentstatus AS ENUM ('completed', 'failed')")
        op.execute(
            "ALTER TABLE documents ALTER COLUMN status TYPE documentstatus USING status::text::documentstatus"
        )
        op.execute("DROP TYPE documentstatus_old")
    else:
        with op.batch_alter_table("documents", schema=None) as batch_op:
            batch_op.alter_column(
                "status",
                existing_type=sa.Enum(
                    "processing", "completed", "failed", name="documentstatus"
                ),
                type_=sa.Enum("completed", "failed", name="documentstatus"),
                existing_nullable=False,
            )
