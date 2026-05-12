from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from fastapi import Query


@dataclass
class PaginationParams:
    """Parámetros de paginación para endpoints."""

    page: int = Query(default=1, ge=1)  # noqa: RUF009
    page_size: int = Query(default=20, ge=1, le=100)  # noqa: RUF009
    order: Literal["asc", "desc"] = Query(default="desc")  # noqa: RUF009


@dataclass
class DateRangeParams:
    """Parámetros de rango de fechas para filtrado."""

    created_after: datetime | None = Query(default=None)  # noqa: RUF009
    created_before: datetime | None = Query(default=None)  # noqa: RUF009
