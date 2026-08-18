import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from core.config import settings
from db.base import Base

logger = logging.getLogger("api.db")

def get_database_url() -> str:
    url = settings.DATABASE_URL
    if not url:
        raise ValueError("DATABASE_URL must be configured in environment (.env).")
    # Ensure async driver for postgresql
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not url.startswith("postgresql+asyncpg://"):
        raise ValueError(f"Unsupported database scheme in DATABASE_URL: {url}. Must be postgresql+asyncpg://")
    return url

db_url = get_database_url()

# Create async engine for PostgreSQL
engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def init_db() -> None:
    """Initialize PostgreSQL database tables asynchronously on startup.
    Fails fast with exception if PostgreSQL is unreachable.
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("PostgreSQL database tables verified and initialized successfully.")
    except Exception as exc:
        safe_url = db_url.split("@")[-1] if "@" in db_url else db_url
        logger.error("DATABASE CONNECTION FAILED on [%s]: %s", safe_url, exc, exc_info=True)
        raise

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session per request."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
