"""rename avatar_url to avatar_path

Revision ID: 635390715f22
Revises: b2e16316a3f3
Create Date: 2026-05-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "635390715f22"
down_revision: Union[str, Sequence[str], None] = "b2e16316a3f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("avatar_url", new_column_name="avatar_path")


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("avatar_path", new_column_name="avatar_url")
