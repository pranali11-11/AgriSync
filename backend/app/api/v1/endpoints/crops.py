from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.crop import Crop

router = APIRouter()


class CropStageItem(BaseModel):
    id: int
    stage_name: str
    start_day: int
    end_day: int
    stage_description: Optional[str] = None
    source: str = "SAMPLE - verify with ICAR / state agriculture dept"

    model_config = ConfigDict(from_attributes=True)


class CropListItem(BaseModel):
    id: int
    name: str
    name_hi: Optional[str]
    name_mr: Optional[str]
    duration_days: int
    category: str = "other"
    stages: List[CropStageItem] = []

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=List[CropListItem])
@router.get("/", response_model=List[CropListItem])
async def list_crops(db: AsyncSession = Depends(get_db)):
    """Retrieve all crops with multilingual names, category, and stages for onboarding wizard."""
    stmt = (
        select(Crop)
        .options(selectinload(Crop.stages))
        .order_by(Crop.category, Crop.name)
    )
    crops = (await db.execute(stmt)).scalars().all()
    return crops


@router.get("/{crop_id}", response_model=CropListItem)
async def get_crop(crop_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve a single crop by ID with full stage definitions and descriptions."""
    stmt = (
        select(Crop)
        .options(selectinload(Crop.stages))
        .where(Crop.id == crop_id)
    )
    crop = (await db.execute(stmt)).scalar_one_or_none()
    if not crop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crop with ID {crop_id} not found"
        )
    return crop
