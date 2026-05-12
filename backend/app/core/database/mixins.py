import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field


def generate_id() -> str:
    """Genera un identificador único (UUID4) como cadena."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Retorna la fecha y hora actual en UTC."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Mixin que agrega el campo created_at con valor por defecto UTC."""

    created_at: datetime = Field(default_factory=utc_now)


class SoftDeleteMixin:
    """Mixin que agrega campos is_deleted y deleted_at para soft-delete."""

    is_deleted: bool = Field(default=False)
    deleted_at: datetime | None = Field(default=None)
