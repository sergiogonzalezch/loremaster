import logging
from collections.abc import Sequence
from typing import TypeVar

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import Select
from sqlmodel import Session, SQLModel, select

from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=SQLModel)


def paginate(
    session: Session,
    base_stmt: Select,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list, int]:
    """Pagina una consulta base con página y tamaño dados.

    Retorna una tupla (items, total) donde items es la página solicitada
    y total es el conteo total de registros.
    """
    skip = (page - 1) * page_size
    total = session.exec(select(func.count()).select_from(base_stmt.subquery())).one()
    items = session.exec(base_stmt.offset(skip).limit(page_size)).all()
    return list(items), total


def paginate_with_sort(
    session: Session,
    model: type[T],
    conditions: Sequence,
    page: int = 1,
    page_size: int = 20,
    order_col=None,
    order: str = "desc",
) -> tuple[list[T], int]:
    """Pagina y ordena una consulta por modelo y condiciones dadas.

    Retorna una tupla (items, total) con paginación y ordenamiento.
    """
    skip = (page - 1) * page_size
    total = session.exec(
        select(func.count()).select_from(select(model).where(*conditions).subquery())
    ).one()
    sort_col = order_col.asc() if order == "asc" else order_col.desc()
    items = session.exec(
        select(model)
        .where(*conditions)
        .order_by(sort_col)
        .offset(skip)
        .limit(page_size)
    ).all()
    return list(items), total


def db_commit(session: Session, operation: str) -> None:
    """Ejecuta commit en la sesión con manejo consistente de errores.

    En caso de error SQLAlchemy, hace rollback y lanza DatabaseError.
    """
    try:
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.exception("DB commit failed during %s", operation)
        raise DatabaseError from e


def get_active_by_id(
    session: Session,
    model: type[T],
    record_id: str,
    collection_id: str,
) -> T | None:
    """Obtiene un registro activo por ID y collection_id, sin soft-deleted."""
    stmt = select(model).where(
        model.id == record_id,
        model.collection_id == collection_id,
        model.is_deleted.is_(False),
    )
    return session.exec(stmt).first()
