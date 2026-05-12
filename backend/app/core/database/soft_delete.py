"""Utilidades para soft-delete de registros en base de datos."""

from datetime import datetime, timezone

from sqlmodel import Session

from app.core.database.utils import db_commit


class SoftDeleteMixin:
    """Mixin que agrega campos de soft-delete a un modelo: is_deleted y deleted_at."""

    is_deleted: bool = False
    deleted_at: datetime | None = None


def soft_delete(session: Session, record) -> bool:
    """Marca un registro como eliminado (soft-delete).

    Actualiza is_deleted, deleted_at y updated_at, y hace commit en la sesión.

    Retorna True si la operación fue exitosa.
    """
    now = datetime.now(timezone.utc)
    record.is_deleted = True
    record.deleted_at = now
    if hasattr(record, "updated_at"):
        record.updated_at = now
    db_commit(session, f"soft delete {record.__class__.__name__}")
    return True
