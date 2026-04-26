"""Add token_count to entity_contents

Revision ID: a1b2c3d4e5f6
Revises: 4b6111255ec7
Create Date: 2026-04-25 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "4b6111255ec7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("entity_contents", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("token_count", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("entity_contents", schema=None) as batch_op:
        batch_op.drop_column("token_count")