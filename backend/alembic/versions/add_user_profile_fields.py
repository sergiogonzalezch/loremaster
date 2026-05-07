"""Add user profile fields

Revision ID: add_user_profile_fields
Revises: add_owner_id_to_collections
Create Date: 2026-05-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_user_profile_fields"
down_revision: Union[str, Sequence[str], None] = "add_owner_id_to_collections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("display_name", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("bio", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("avatar_url", sa.String(500), nullable=True))
        batch_op.create_index("ix_users_email", ["email"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_email")
        batch_op.drop_column("avatar_url")
        batch_op.drop_column("bio")
        batch_op.drop_column("display_name")
        batch_op.drop_column("email")