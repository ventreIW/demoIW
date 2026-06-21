from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_session)) -> ORJSONResponse:
    try:
        await session.execute(text("SELECT 1"))
        return ORJSONResponse({"status": "ok", "db": "connected"})
    except Exception:
        return ORJSONResponse(
            {"status": "degraded", "db": "unavailable"},
            status_code=503,
        )
