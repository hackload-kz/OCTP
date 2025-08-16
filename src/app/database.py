from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import Engine
from sqlalchemy import MetaData
from sqlalchemy import NullPool
from sqlalchemy import log as sqlachemy_log
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from config import Settings

# Disable SQLAlchemy logging
sqlachemy_log._add_default_handler = lambda x: None

# Custom constraint naming conventions
# https://docs.sqlalchemy.org/en/20/core/constraints.html#constraint-naming-conventions
db_naming_convention = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for SQLAlchemy models."""

    metadata = MetaData(naming_convention=db_naming_convention)


engine: Engine | AsyncEngine | None = None
SessionLocal: sessionmaker = sessionmaker(
    class_=AsyncSession,
    autoflush=False,
    # recommended by the SQLAlchemy docs on asyncio
    # https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#asyncio-orm-avoid-lazyloads
    expire_on_commit=False,
)


def set_async_engine(settings: Settings):
    global engine, SessionLocal
    options = {
        "echo": settings.DEBUG and not settings.ENV,
        "pool_size": settings.DB_POOL_SIZE,
        "pool_recycle": settings.DB_POOL_TTL,
        "pool_pre_ping": settings.DB_POOL_PRE_PING,
        # https://github.com/psycopg/psycopg/issues/911
        "connect_args": {"prepare_threshold": None},
    }
    if settings.USE_PGBOUNCER:
        del options["pool_size"]
        options["poolclass"] = NullPool

    # https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#dialect-postgresql-psycopg-url
    engine = create_async_engine(settings.POSTGRES_URL, **options)
    SessionLocal.configure(bind=engine)


# async helpers as FastAPI dependencies
async def get_connection() -> AsyncGenerator[AsyncConnection, None]:
    async with engine.connect() as conn:
        yield conn


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    if hasattr(request.state, "db"):
        yield request.state.db
    else:
        async with SessionLocal() as session:
            yield session


@asynccontextmanager
async def transaction(session: AsyncSession):
    """Transaction context manager for committing and rolling back."""
    async with session.begin():
        try:
            yield
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
