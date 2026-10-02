from typing import List, Optional
from fastapi import APIRouter, Depends
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
