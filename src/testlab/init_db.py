"""CLI: создание схемы БД."""

import asyncio
import sys

import testlab.models  # noqa: F401 — регистрирует модели в Base.metadata
from testlab.database import async_engine, init_db


async def _run(drop: bool) -> None:
    await init_db(async_engine, drop=drop)
    await async_engine.dispose()
    print(f"БД готова: {async_engine.url}")


def main() -> None:
    asyncio.run(_run(drop="--reset" in sys.argv))


if __name__ == "__main__":
    main()
