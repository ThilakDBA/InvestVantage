from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


class Database:
    """Owns the SQLAlchemy engine and session factory."""

    def __init__(self, database_url: str) -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(
            database_url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    def session(self) -> Generator[Session, None, None]:
        with self.session_factory() as database_session:
            yield database_session

    def dispose(self) -> None:
        self.engine.dispose()
