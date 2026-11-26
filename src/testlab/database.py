"""Движок, сессии и создание схемы."""

from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from testlab.config.app_config import settings


class Base(DeclarativeBase):
    pass


def enable_sqlite_foreign_keys(engine: AsyncEngine) -> None:
    """SQLite не применяет ON DELETE CASCADE без PRAGMA на каждом соединении.

    PRAGMA выполняется в событии "begin": внутри "connect" aiosqlite ещё не
    отдаёт синхронный доступ к курсору, а PRAGMA не действует внутри уже
    начатой транзакции.
    """
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine.sync_engine, "begin")
    def _set_foreign_keys(connection) -> None:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def create_engine(url: str, echo: bool = False) -> AsyncEngine:
    engine = create_async_engine(url, echo=echo)
    enable_sqlite_foreign_keys(engine)
    return engine


async_engine = create_engine(settings.db.url, settings.db.echo)
async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        yield session


async def init_db(engine: AsyncEngine, drop: bool = False) -> None:
    async with engine.begin() as conn:
        if drop:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
