"""Database manager for async SQLite operations."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Default to SQLite in data directory
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/arbitrage.db")

# Create async engine
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# Create session factory
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session context manager.

    Usage:
        async with get_db() as session:
            # Use session
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    from src.database.models import Base

    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized")


async def close_db() -> None:
    """Close database connections."""
    await async_engine.dispose()
    logger.info("Database connections closed")


async def get_session() -> AsyncSession:
    """
    Get a database session.

    Remember to close the session when done.
    """
    return AsyncSessionLocal()
