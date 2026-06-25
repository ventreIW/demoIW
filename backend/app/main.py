from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.infrastructure.database import engine
from app.infrastructure.logging import setup_logging
from app.routers.health import router as health_router
from app.routers.scenarios import router as scenarios_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs" if settings.APP_ENV == "development" else None,
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(scenarios_router)
    return app


app = create_app()
