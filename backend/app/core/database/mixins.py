import uuid
from datetime import datetime, timezone
from typing import Optional, TypeVar

from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel

T = TypeVar("T", bound="TimestampedModel")


def generate_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: datetime = Field(default_factory=utc_now)


class SoftDeleteMixin:
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)


class TimestampedModel(SQLModel, TimestampMixin, table=True):
    pass


class TimestampedSoftDeleteModel(TimestampedModel, SoftDeleteMixin, table=True):
    pass


class UUIDPrimaryKey:
    id: str = Field(
        default_factory=generate_id,
        primary_key=True,
        max_length=36,
    )
