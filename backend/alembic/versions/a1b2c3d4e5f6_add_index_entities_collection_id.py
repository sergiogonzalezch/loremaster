"""add index entities collection_id

Revision ID: a1b2c3d4e5f6
Revises: 4332793740fb
Create Date: 2026-05-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "4332793740fb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Añade índice en entities.collection_id para acelerar queries por colección."""
    op.create_index("ix_entities_collection_id", "entities", ["collection_id"], if_not_exists=True)


def downgrade() -> None:
    """Elimina el índice en entities.collection_id."""
    op.drop_index("ix_entities_collection_id", table_name="entities")
