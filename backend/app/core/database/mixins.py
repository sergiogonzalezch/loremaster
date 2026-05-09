import uuid
from datetime import datetime, timezone
from typing import Optional, TypeVar

from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel

T = TypeVar("T", bound="TimestampedModel")


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
    deleted_at: Optional[datetime] = Field(default=None)


class TimestampedModel(SQLModel, TimestampMixin, table=True):
    """Modelo base con timestamp de creación."""

    pass


class TimestampedSoftDeleteModel(TimestampedModel, SoftDeleteMixin, table=True):
    """Modelo base con timestamp y soft-delete."""

    pass


class UUIDPrimaryKey:
    """Mixin que agrega un campo id como clave primaria UUID."""

    id: str = Field(
        default_factory=generate_id,
        primary_key=True,
        max_length=36,
    )
