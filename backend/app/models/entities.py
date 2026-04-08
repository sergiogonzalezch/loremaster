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

class Entity(SQLModel, table=True):
    __tablename__ = "entities"

    id: str = Field(default_factory=_new_id, primary_key=True, max_length=36)
    collection_id: str = Field(index=True, max_length=36)
    name: str = Field(max_length=255)
    description: str = Field(default="", max_length=2000)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(default=None)


# ── API schemas (Pydantic — no generan tablas) ────────────────────────────────

class CreateEntityRequest(BaseModel):
    name: str
    description: str = ""


class UpdateEntityRequest(BaseModel):
    name: str
    description: str = ""


class EntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    collection_id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class EntityListResponse(BaseModel):
    data: List[EntityResponse]
    count: int
