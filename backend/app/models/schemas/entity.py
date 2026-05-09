from datetime import datetime

from pydantic import BaseModel, Field

from app.models.db.entity import EntityType


class EntityRequest(BaseModel):
    type: EntityType
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


CreateEntityRequest = EntityRequest


class UpdateEntityRequest(BaseModel):
    type: EntityType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class EntityResponse(BaseModel):
    id: str
    collection_id: str
    type: EntityType
    name: str
    description: str
    created_at: datetime
    updated_at: datetime | None = None
