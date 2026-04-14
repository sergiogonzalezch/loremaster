from sqlmodel import SQLModel, create_engine
from config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False,
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
