from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session


class SoftDeleteMixin:
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None


def soft_delete(session: Session, record) -> bool:
    from app.core.common import db_commit

    now = datetime.now(timezone.utc)
    record.is_deleted = True
    record.deleted_at = now
    if hasattr(record, "updated_at"):
        record.updated_at = now
    db_commit(session, f"soft delete {record.__class__.__name__}")
    return True
