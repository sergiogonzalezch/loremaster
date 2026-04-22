import math
from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    meta: PaginationMeta

    @classmethod
    def build(
        cls, items: list, total: int, page: int, page_size: int
    ) -> "PaginatedResponse":
        return cls(
            data=items,
            meta=PaginationMeta(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=math.ceil(total / page_size) if total else 0,
            ),
        )