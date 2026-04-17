from typing import List, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import SQLModel, Field as SQLField
import uuid

# ── Tabla DB ──────────────────────────────────────────────────────────────────


class Collection(SQLModel, table=True):
    __tablename__ = "collections"

    id: str = SQLField(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=36
    )
    name: str = SQLField(index=True, unique=True, max_length=255)
    description: str = SQLField(default="", max_length=2000)
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = SQLField(default=None)
    is_deleted: bool = SQLField(default=False)
    deleted_at: Optional[datetime] = SQLField(default=None)


# ── API schemas ───────────────────────────────────────────────────────────────


class CreateCollectionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)


class CollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class CollectionListResponse(BaseModel):
    data: List[CollectionResponse]
    count: int
