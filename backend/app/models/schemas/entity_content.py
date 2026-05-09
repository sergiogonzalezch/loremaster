from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.models.enums import ContentCategory, ContentStatus


class EntityContentResponse(BaseModel):
    id: str
    entity_id: str
    collection_id: str
    generated_text_id: str
    category: ContentCategory
    content: str
    raw_content: Optional[str] = None
    was_edited: bool = False
    query: Optional[str] = None
    sources_count: int = 0
    token_count: int = 0
    status: ContentStatus
    is_shared: bool = False
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="after")
    def compute_was_edited(self) -> "EntityContentResponse":
        if self.raw_content is not None:
            object.__setattr__(self, "was_edited", self.content != self.raw_content)
        return self


class GenerateContentRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=2000)


class UpdateContentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class ShareContentRequest(BaseModel):
    shared: bool
