from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from testlab.config.app_config import settings

class Base(DeclarativeBase):
    pass

engine = create_async_engine(settings.db.url, echo=settings.db.echo)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with async_session_maker() as session:
        yield session