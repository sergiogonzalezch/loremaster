from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SharedContentSummary(BaseModel):
    id: str
    content: str
    category: str
    entity_name: str
    entity_type: str
    confirmed_at: Optional[datetime] = None
    created_at: datetime


class SharedImageSummary(BaseModel):
    id: str
    generation_id: str
    image_url: Optional[str] = None
    storage_path: Optional[str] = None
    seed: int
    auto_prompt: str
    final_prompt: str
    entity_name: str
    entity_type: str
    created_at: datetime


class PublicProfileResponse(BaseModel):
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    shared_contents: list[SharedContentSummary] = []
    shared_images: list[SharedImageSummary] = []


class PublicFeedItem(BaseModel):
    content_id: str
    content: str
    content_preview: str
    category: str
    entity_name: str
    entity_type: str
    owner_username: str
    owner_display_name: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime


class PublicImageItem(BaseModel):
    image_id: str
    generation_id: str
    image_url: Optional[str] = None
    storage_path: Optional[str] = None
    seed: int
    auto_prompt: str
    final_prompt: str
    entity_name: str
    entity_type: str
    owner_username: str
    owner_display_name: Optional[str] = None
    created_at: datetime
