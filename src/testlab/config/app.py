# Здесь будут все собранные настройки приложения

from contextlib import asynccontextmanager
from fastapi import FastAPI

from testlab.routers.user import router as user_router
from testlab.config.base import Base
from testlab.config.db import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="TestLab API", lifespan=lifespan)
app.include_router(user_router)

@app.get("/")
def read_root():
    return {"message": "API is running"}