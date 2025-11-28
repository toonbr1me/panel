from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

from config import (
    ECHO_SQL_QUERIES,
    SQLALCHEMY_DATABASE_URL,
    SQLALCHEMY_MAX_OVERFLOW,
    SQLALCHEMY_POOL_SIZE,
)


def normalize_database_url(url: str) -> str:
    """
    Normalize the database URL to ensure async drivers are used.

    SQLite URLs must use the aiosqlite driver for async operations.
    Converts 'sqlite:///' to 'sqlite+aiosqlite:///' if needed.
    """
    if url.startswith("sqlite:") and not url.startswith("sqlite+"):
        # Replace 'sqlite:' with 'sqlite+aiosqlite:' for async compatibility
        return url.replace("sqlite:", "sqlite+aiosqlite:", 1)
    return url


DATABASE_URL = normalize_database_url(SQLALCHEMY_DATABASE_URL)
IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    engine = create_async_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}, echo=ECHO_SQL_QUERIES
    )
else:
    engine = create_async_engine(
        DATABASE_URL,
        pool_size=SQLALCHEMY_POOL_SIZE,
        max_overflow=SQLALCHEMY_MAX_OVERFLOW,
        pool_recycle=300,
        pool_timeout=5,
        pool_pre_ping=True,
        echo=ECHO_SQL_QUERIES,
    )

SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase, MappedAsDataclass, AsyncAttrs):
    pass


class GetDB:  # Context Manager
    def __init__(self):
        self.db = SessionLocal()

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is not None:
                # Rollback on any exception
                await self.db.rollback()
        except Exception:
            pass
        finally:
            # Always close the session to return connection to pool
            try:
                await self.db.close()
            except Exception:
                pass


async def get_db():  # Dependency
    async with GetDB() as db:
        yield db
