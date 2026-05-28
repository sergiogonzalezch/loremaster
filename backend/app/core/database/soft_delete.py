"""Utilidades para soft-delete de registros en base de datos."""

from datetime import UTC, datetime

from sqlmodel import Session

from app.core.database.utils import db_commit


class SoftDeleteMixin:
    """Mixin que agrega campos de soft-delete a un modelo: is_deleted y deleted_at."""

    is_deleted: bool = False
    deleted_at: datetime | None = None


def soft_delete(session: Session, record: SoftDeleteMixin, *, commit: bool = True) -> bool:
    """Marca un registro como eliminado (soft-delete).

    Actualiza is_deleted, deleted_at y updated_at.
    Con commit=True (default) hace commit inmediato — correcto para operaciones
    de un solo elemento. Con commit=False acumula el cambio sin commitear,
    permitiendo que operaciones de cascada los agrupen en una sola transacción.

    Retorna True si la operación fue exitosa.
    """
    now = datetime.now(UTC)
    record.is_deleted = True
    record.deleted_at = now
    if hasattr(record, "updated_at"):
        record.updated_at = now
    session.add(record)
    if commit:
        db_commit(session, f"soft delete {record.__class__.__name__}")
    return True
