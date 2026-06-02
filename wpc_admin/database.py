import os
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wpc.db")
engine = create_engine(DATABASE_URL, echo=False)


def create_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator:
    with Session(engine) as session:
        yield session
