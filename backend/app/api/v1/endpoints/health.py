from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
async def check_health(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    AgriSync Health Check Endpoint
    Verifies API status, Database (PostGIS) connection, and Redis cache availability.
    """
    db_status = "disconnected"
    db_version = None
    redis_status = "disconnected"

    # Check Database Connection
    try:
        result = await db.execute(text("SELECT 1;"))
        if result.scalar() == 1:
            db_status = "connected"
            postgis_check = await db.execute(text("SELECT PostGIS_Full_Version();"))
            db_version = postgis_check.scalar()
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Check Redis Connection
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_timeout=2)
        if await r.ping():
            redis_status = "connected"
        await r.close()
    except Exception as e:
        redis_status = f"error: {str(e)}"

    overall_status = "healthy" if db_status == "connected" and redis_status == "connected" else "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "components": {
            "database": {
                "status": db_status,
                "postgis_info": db_version or "N/A"
            },
            "redis": {
                "status": redis_status
            }
        }
    }
