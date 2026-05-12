"""
Async PostgreSQL connection pool using SQLAlchemy.
Uses asyncpg driver under the hood for non-blocking I/O.
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Expects: postgresql+asyncpg://user:password@host:port/dbname
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/gateway"
)

engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,          # Connections kept open
    max_overflow=20,       # Extra connections under burst load
    pool_pre_ping=True,    # Verify connections before using (handles dropped connections)
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db():
    """FastAPI dependency: yields an async DB session and ensures cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def init_db():
    """Create all tables on startup. Safe to run multiple times."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
