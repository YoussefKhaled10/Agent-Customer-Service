from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.helpers.config import settings


engine: Engine = create_engine(
    settings.POSTGRES_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)


SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


@contextmanager
def database_session() -> Generator[Session, None, None]:
    """Create a transactional database session.

    The session is committed when the block succeeds, rolled back when an
    exception occurs, and closed in all cases.
    """
    session = SessionLocal()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_database_connection() -> dict[str, Any]:
    """Verify the PostgreSQL connection and return basic server details."""
    statement = text(
        """
        SELECT
            current_database() AS database_name,
            current_user AS database_user,
            current_setting('server_version') AS database_version
        """
    )

    with engine.connect() as connection:
        result = connection.execute(statement).mappings().one()

    return {
        "database_name": result["database_name"],
        "database_user": result["database_user"],
        "database_version": result["database_version"],
    }


def dispose_database_engine() -> None:
    """Close all pooled database connections, mainly for tests and shutdown."""
    engine.dispose()
