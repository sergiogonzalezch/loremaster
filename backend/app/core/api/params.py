"""Parámetros de consulta reutilizables para paginación y filtros."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from fastapi import Query


@dataclass
class PaginationParams:
    """Parámetros de paginación para endpoints."""

    page: int = Query(default=1, ge=1)
    page_size: int = Query(default=20, ge=1, le=100)
    order: Literal["asc", "desc"] = Query(default="desc")


@dataclass
class DateRangeParams:
    """Parámetros de rango de fechas para filtrado."""

    created_after: datetime | None = Query(default=None)
    created_before: datetime | None = Query(default=None)
