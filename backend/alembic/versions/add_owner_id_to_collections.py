"""Add owner_id to collections

Revision ID: add_owner_id_to_collections
Revises: e4f13f52affc
Create Date: 2026-05-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "add_owner_id_to_collections"
down_revision: Union[str, Sequence[str], None] = "e4f13f52affc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("collections") as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.String(36), nullable=True))
        batch_op.drop_index(batch_op.f("ix_collections_name"))
        batch_op.create_index("ix_collections_owner_id", ["owner_id"])
        batch_op.create_unique_constraint(
            "uq_collection_name_owner", ["name", "owner_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("collections") as batch_op:
        batch_op.drop_constraint("uq_collection_name_owner", type_="unique")
        batch_op.drop_index("ix_collections_owner_id")
        batch_op.create_index("ix_collections_name", ["name"], unique=True)
        batch_op.drop_column("owner_id")