import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, select
from sqlalchemy.orm import selectinload
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.crop import Crop
from app.services.crop_validation import validate_crop_stages_integrity
from app.api.v1.router import api_router
from app.services.scheme_notifications import create_due_scheme_notifications

logger = logging.getLogger(__name__)


async def scheme_notification_loop():
    while True:
        try:
            async with AsyncSessionLocal() as db:
                subscriptions_exist = await db.run_sync(
                    lambda session: inspect(session.bind).has_table(
                        "scheme_notification_preferences"
                    )
                )
                if subscriptions_exist:
                    await create_due_scheme_notifications(db)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Failed to check upcoming scheme deadlines")
        await asyncio.sleep(24 * 60 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation: verify crop stages are contiguous with zero gaps/overlaps
    async with AsyncSessionLocal() as db:
        stmt = select(Crop).options(selectinload(Crop.stages))
        crops = (await db.execute(stmt)).scalars().all()
        if crops:
            stage_errors = validate_crop_stages_integrity(crops)
            if stage_errors:
                err_summary = (
                    f"FATAL: Crop stage validation failed at startup ({len(stage_errors)} error(s)):\n"
                    + "\n".join(stage_errors)
                )
                logger.critical(err_summary)
                raise RuntimeError(err_summary)
            logger.info("Crop stages startup check: All crops have contiguous, valid stages.")

    task = asyncio.create_task(scheme_notification_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Serve uploaded machine photos from local disk in dev
_media_dir = Path(__file__).resolve().parent.parent / "media"
_media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")

# Set CORS origins
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "message": "Welcome to AgriSync API - Multilingual Crop Advisory & Machinery Sharing Platform",
        "health_check": f"{settings.API_V1_STR}/health",
        "docs": f"{settings.API_V1_STR}/docs"
    }
