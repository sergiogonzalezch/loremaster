from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

from fastapi import Query


@dataclass
class PaginationParams:
    page: int = Query(default=1, ge=1)
    page_size: int = Query(default=20, ge=1, le=100)
    order: Literal["asc", "desc"] = Query(default="desc")


@dataclass
class DateRangeParams:
    created_after: Optional[datetime] = Query(default=None)
    created_before: Optional[datetime] = Query(default=None)
