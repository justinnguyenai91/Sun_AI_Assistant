"""
Database connection and session management.
"""
import os
import logging
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from .conversation import Base

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sun_user:sun_pass_2026@localhost:5432/sun_mes")
DATABASE_ENABLED = os.getenv("DATABASE_ENABLED", "true").lower() in ("true", "1", "yes")

# Convert postgresql:// to postgresql+asyncpg:// for async
if DATABASE_URL.startswith("postgresql://"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Sync engine for migrations
sync_engine = create_engine(
    DATABASE_URL.replace("+asyncpg", ""),
    pool_pre_ping=True,
    echo=False
)

# Async engine for application
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    pool_size=10,
    max_overflow=20
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """Initialize database tables."""
    if not DATABASE_ENABLED:
        logger.info("Database disabled, skipping initialization")
        return
    
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")


@asynccontextmanager
async def get_db_session():
    """Get async database session."""
    if not DATABASE_ENABLED:
        yield None
        return
    
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def cleanup_db():
    """Cleanup database connections."""
    if DATABASE_ENABLED:
        await async_engine.dispose()
