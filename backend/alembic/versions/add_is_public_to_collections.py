"""Add is_public to collections

Revision ID: add_is_public_to_collections
Revises: add_user_profile_fields
Create Date: 2026-05-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_is_public_to_collections"
down_revision: Union[str, Sequence[str], None] = "add_user_profile_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("collections") as batch_op:
        batch_op.add_column(
            sa.Column("is_public", sa.Boolean(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("collections") as batch_op:
        batch_op.drop_column("is_public")