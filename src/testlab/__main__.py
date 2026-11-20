# Здесь будет создание приложения и запуск uvicorn

from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from testlab.database import engine, Base
from testlab.routers.user import router as user_router
import testlab.models.user 

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

def create_app() -> FastAPI:
    app = FastAPI(title="TestLab API", lifespan=lifespan)
    app.include_router(user_router)
    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("testlab.__main__:app", host="127.0.0.1", port=8000, reload=True)