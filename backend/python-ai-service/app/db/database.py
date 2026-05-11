"""
Async SQLAlchemy engine + session factory backed by SQLite.

A single `jarvis.db` file lives in the data directory so the database
persists across container restarts when the data volume is mounted.
All tables are created automatically on first startup.
"""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# ─── Path ─────────────────────────────────────────────────────────────────────

_DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
_DATA_DIR.mkdir(parents=True, exist_ok=True)

_DB_URL = f"sqlite+aiosqlite:///{_DATA_DIR / 'jarvis.db'}"

# ─── Engine + session factory ─────────────────────────────────────────────────

engine = create_async_engine(
    _DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ─── Base class ───────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create all tables defined in models.py (idempotent)."""
    # Import models so SQLAlchemy sees them before creating tables
    import app.db.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a scoped async session."""
    async with _session_factory() as session:
        yield session
