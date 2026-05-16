"""
Async PostgreSQL connection pool using SQLAlchemy.
Uses asyncpg driver under the hood for non-blocking I/O.
"""
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Explicitly load .env
load_dotenv()

# Expects: postgresql+asyncpg://user:password@host:port/dbname
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("WARNING: DATABASE_URL not found in .env! Falling back to localhost default.")
    DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/gateway"
else:
    # Redact password for logs
    safe_url = DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL
    print(f"Database: Attempting connection to host: {safe_url}")

# Determine if SSL is required (usually for Neon/Prod, not for local Docker)
ssl_mode = "require" if "neon.tech" in DATABASE_URL or os.getenv("DB_SSL", "false").lower() == "true" else None

connect_args = {}
if ssl_mode:
    connect_args["ssl"] = ssl_mode

engine = create_async_engine(
    DATABASE_URL,
    connect_args=connect_args,
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
