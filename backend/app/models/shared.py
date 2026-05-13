"""Utilidades compartidas para respuestas paginadas."""

import math
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Metadatos de paginación incluidos en respuestas paginadas.

    Attributes:
        total: Número total de elementos disponibles.
        page: Página actual (1-indexed).
        page_size: Cantidad de elementos por página.
        total_pages: Total de páginas calculadas.

    """

    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Respuesta estándar paginada para endpoints de listado.

    Attributes:
        data: Lista de elementos de la página actual.
        meta: Metadatos de paginación.

    Type Parameters:
        T: Tipo de los elementos contenidos en data.

    """

    data: list[T]
    meta: PaginationMeta

    @classmethod
    def build(
        cls, items: list, total: int, page: int, page_size: int,
    ) -> "PaginatedResponse":
        """Construye una respuesta paginada a partir de los items y metadatos."""
        return cls(
            data=items,
            meta=PaginationMeta(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=math.ceil(total / page_size) if total else 0,
            ),
        )
