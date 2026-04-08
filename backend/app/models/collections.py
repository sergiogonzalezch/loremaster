from typing import List, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from sqlmodel import SQLModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    import uuid
    return str(uuid.uuid4())


# ── Tabla DB ──────────────────────────────────────────────────────────────────

class Collection(SQLModel, table=True):
    __tablename__ = "collections"

    id: str = Field(default_factory=_new_id, primary_key=True, max_length=36)
    name: str = Field(index=True, unique=True, max_length=255)
    description: str = Field(default="", max_length=2000)
    status: str = Field(default="active", max_length=50)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)


# ── API schemas ───────────────────────────────────────────────────────────────

class CreateCollectionRequest(BaseModel):
    name: str
    description: str = ""


class CollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


class CollectionListResponse(BaseModel):
    data: List[CollectionResponse]
    count: int
