"""data_fix_orphan_image_generations

Marca como soft-deleted las ImageGenerations huérfanas: aquellas con
is_deleted=false cuyos ImageRecords están todos soft-deleted. Estado
inconsistente generado por el bug en delete_image_service previo al fix
de la sesión 2026-05-28, que solo soft-deletaba el ImageRecord sin
verificar si era el último de la generación.

La migración es idempotente: el filtro NOT EXISTS solo afecta a las
generaciones que actualmente sin records activos. Re-ejecuciones son no-op.

Revision ID: 782abfe638bf
Revises: a1b2c3d4e5f6
Create Date: 2026-05-28 11:17:19.741962

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "782abfe638bf"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Limpia ImageGenerations huérfanas: marca is_deleted=true cuando todos
    sus ImageRecords ya están soft-deleted. CURRENT_TIMESTAMP funciona en
    SQLite y PostgreSQL.
    """
    op.execute(
        """
        UPDATE image_generations
        SET is_deleted = TRUE,
            deleted_at = CURRENT_TIMESTAMP
        WHERE is_deleted = FALSE
          AND NOT EXISTS (
              SELECT 1 FROM image_records
              WHERE image_records.generation_id = image_generations.id
                AND image_records.is_deleted = FALSE
          )
        """
    )


def downgrade() -> None:
    """No-op: no podemos distinguir entre generaciones limpiadas por esta
    migración y generaciones que ya estaban soft-deletadas legítimamente
    por el usuario. Dejar el estado actual es seguro.
    """
    pass
