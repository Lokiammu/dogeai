"""Async SQLAlchemy engine and session factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.pool_min_size,
    max_overflow=settings.pool_max_size - settings.pool_min_size,
    pool_pre_ping=True,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency — yields a transactional async session."""
    async with AsyncSessionLocal() as session:
        yield session
