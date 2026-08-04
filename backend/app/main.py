import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.infrastructure.database import engine
from app.infrastructure.logging import setup_logging
from app.routers.cases import router as cases_router
from app.routers.executive import router as executive_router
from app.routers.health import router as health_router
from app.routers.scenarios import router as scenarios_router

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    if not settings.OPENROUTER_API_KEY:
        log.warning(
            "OPENROUTER_API_KEY is empty — LLM enrichment is DISABLED. "
            "Generated scenarios will contain raw Faker company names (enriched=false)."
        )
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
    app.include_router(cases_router)
    app.include_router(executive_router)
    return app


app = create_app()
