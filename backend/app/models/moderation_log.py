from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class ModerationLog(SQLModel, table=True):
    __tablename__ = "moderation_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    layer: str  # "input" | "document" | "output"
    snippet: str = Field(max_length=200)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
