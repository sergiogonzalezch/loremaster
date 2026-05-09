from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateCollectionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)


class UpdateCollectionRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class CollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    document_count: int = 0
    entity_count: int = 0
