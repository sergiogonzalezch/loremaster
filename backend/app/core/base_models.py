# Backward compatibility - re-exports from database.mixins
from app.core.database.mixins import (
    generate_id,
    utc_now,
    TimestampMixin,
    SoftDeleteMixin,
    TimestampedModel,
    TimestampedSoftDeleteModel,
    UUIDPrimaryKey,
)
