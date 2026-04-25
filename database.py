"""
db/database.py
==============
Async SQLAlchemy database engine and session management.
Uses SQLite (aiosqlite) by default — swap DATABASE_URL for PostgreSQL in production.
"""

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config.settings import settings

# ── Engine ─────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,      # SQL logging in debug mode
    future=True,
    connect_args={"timeout": 30},
)

# ── Session factory ────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Base class for all ORM models ──────────────────────
class Base(DeclarativeBase):
    pass


# ── FastAPI dependency: yields a DB session per request ─
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Create all tables ──────────────────────────────────
async def init_db():
    """Called once at application startup to create tables."""
    async with engine.begin() as conn:
        if settings.DATABASE_URL.startswith("sqlite"):
            try:
                await conn.execute(text("PRAGMA journal_mode=WAL"))
                await conn.execute(text("PRAGMA synchronous=NORMAL"))
                await conn.execute(text("PRAGMA busy_timeout=30000"))
            except OperationalError:
                # If another local process is holding the SQLite file, continue with
                # default journal settings instead of failing application startup.
                pass
        await conn.run_sync(Base.metadata.create_all)
