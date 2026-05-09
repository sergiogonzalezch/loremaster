from pydantic import BaseModel, ConfigDict


class FromAttributesMixin(BaseModel):
    model_config = ConfigDict(from_attributes=True)


from app.core.api.params import PaginationParams, DateRangeParams
from app.core.api.filters import _CONTENT_CONDITIONS, _IMAGE_CONDITIONS

__all__ = [
    "FromAttributesMixin",
    "PaginationParams",
    "DateRangeParams",
    "_CONTENT_CONDITIONS",
    "_IMAGE_CONDITIONS",
]
