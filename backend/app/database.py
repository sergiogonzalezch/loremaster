from collections.abc import Generator

from sqlalchemy import Engine
from sqlmodel import SQLModel, Session, create_engine
from app.core.config import settings


def _build_engine() -> Engine:
    # To switch SQL backends change DATABASE_URL in .env.
    # Add engine-specific kwargs here if the new engine requires them
    # (e.g. pool_size, max_overflow, ssl args for MySQL/Aurora, etc.).
    kwargs: dict = {}
    if settings.database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_pre_ping"] = True
    return create_engine(settings.database_url, **kwargs)


engine = _build_engine()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
