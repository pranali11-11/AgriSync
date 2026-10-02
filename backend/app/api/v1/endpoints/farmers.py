from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from geoalchemy2.elements import WKTElement

from app.core.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User, FarmerProfile
from app.models.crop import Crop, CropStage
from app.models.farm import Farm, SoilTest
from app.schemas.farm import validate_irrigation_input

router = APIRouter()

# --- Pydantic Request / Response Models ---

class UserUpdate(BaseModel):
    name: str = Field(..., min_length=2, max_length=60)
    language: Optional[str] = Field(None, pattern="^(en|hi|mr)$")


class UserMeResponse(BaseModel):
    id: int
    name: str
    phone: str
    role: str
    language: str

    model_config = ConfigDict(from_attributes=True)


class FarmerProfilePayload(BaseModel):
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = "Maharashtra"
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    total_area_acres: float = Field(0.0, ge=0)


class FarmerProfileResponse(BaseModel):
    user_id: int
    village: Optional[str]
    district: Optional[str]
    state: Optional[str]
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    total_area_acres: float

    model_config = ConfigDict(from_attributes=True)


class FarmCreatePayload(BaseModel):
    crop_id: int
    sowing_date: date
    area_acres: float = Field(..., gt=0)
    soil_type: Optional[str] = None
    irrigation_type: Optional[str] = None
    irrigation_type_note: Optional[str] = None

    @model_validator(mode="after")
    def check_irrigation(self):
        norm_type, norm_note = validate_irrigation_input(self.irrigation_type, self.irrigation_type_note)
        self.irrigation_type = norm_type
        self.irrigation_type_note = norm_note
        return self


class FarmResponse(BaseModel):
    id: int
    farmer_id: int
    crop_id: int
    sowing_date: date
    area_acres: float
    soil_type: Optional[str]
    current_stage: Optional[str]
    irrigation_type: Optional[str]
    irrigation_type_note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SoilTestPayload(BaseModel):
    ph: float = Field(..., ge=0, le=14)
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    organic_carbon: Optional[float] = None
    tested_on: date = Field(default_factory=date.today)


class SoilTestResponse(BaseModel):
    id: int
    farm_id: int
    ph: float
    nitrogen: Optional[float]
    phosphorus: Optional[float]
    potassium: Optional[float]
    organic_carbon: Optional[float]
    tested_on: date

    model_config = ConfigDict(from_attributes=True)


# --- Helper Functions ---

async def calculate_crop_stage(db: AsyncSession, crop_id: int, sowing_date: date) -> str:
    """Auto-computes current crop stage based on days elapsed since sowing date."""
    days_elapsed = max(0, (date.today() - sowing_date).days)
    stmt = select(CropStage).where(CropStage.crop_id == crop_id).order_by(CropStage.start_day)
    stages = (await db.execute(stmt)).scalars().all()

    if not stages:
        return "Active Growth"

    for stage in stages:
        if stage.start_day <= days_elapsed <= stage.end_day:
            return stage.stage_name

    # If beyond max stage end day
    if days_elapsed > stages[-1].end_day:
        return stages[-1].stage_name

    return stages[0].stage_name


# --- Endpoints ---

@router.get("/me", response_model=UserMeResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserMeResponse)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    current_user.name = payload.name.strip()
    if payload.language is not None:
        current_user.language = payload.language

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/farmer/profile", response_model=FarmerProfileResponse)
async def get_farmer_profile(
    current_user: User = Depends(require_role("farmer", "admin")),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(FarmerProfile).where(FarmerProfile.user_id == current_user.id)
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer profile not found")

    return profile


@router.post("/farmer/profile", response_model=FarmerProfileResponse, status_code=status.HTTP_201_CREATED)
@router.put("/farmer/profile", response_model=FarmerProfileResponse)
async def create_or_update_farmer_profile(
    payload: FarmerProfilePayload,
    current_user: User = Depends(require_role("farmer", "admin")),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(FarmerProfile).where(FarmerProfile.user_id == current_user.id)
    profile = (await db.execute(stmt)).scalar_one_or_none()

    location_wkt = None
    if payload.latitude is not None and payload.longitude is not None:
        location_wkt = f"POINT({payload.longitude} {payload.latitude})"

    if not profile:
        profile = FarmerProfile(
            user_id=current_user.id,
            village=payload.village,
            district=payload.district,
            state=payload.state,
            location=location_wkt,
            total_area_acres=payload.total_area_acres
        )
        db.add(profile)
    else:
        profile.village = payload.village
        profile.district = payload.district
        profile.state = payload.state
        if location_wkt:
            profile.location = location_wkt
        profile.total_area_acres = payload.total_area_acres

    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/farms", response_model=List[FarmResponse])
async def list_farmer_farms(
    current_user: User = Depends(require_role("farmer", "admin")),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Farm).where(Farm.farmer_id == current_user.id).order_by(Farm.id.desc())
    farms = (await db.execute(stmt)).scalars().all()
    return farms


@router.post("/farms", response_model=FarmResponse, status_code=status.HTTP_201_CREATED)
async def create_farm(
    payload: FarmCreatePayload,
    current_user: User = Depends(require_role("farmer", "admin")),
    db: AsyncSession = Depends(get_db)
):
    # Verify crop exists
    stmt_crop = select(Crop).where(Crop.id == payload.crop_id)
    crop = (await db.execute(stmt_crop)).scalar_one_or_none()
    if not crop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")

    # Auto-calculate crop stage
    computed_stage = await calculate_crop_stage(db, payload.crop_id, payload.sowing_date)

    farm = Farm(
        farmer_id=current_user.id,
        crop_id=payload.crop_id,
        sowing_date=payload.sowing_date,
        area_acres=payload.area_acres,
        soil_type=payload.soil_type,
        current_stage=computed_stage,
        irrigation_type=payload.irrigation_type,
        irrigation_type_note=payload.irrigation_type_note
    )
    db.add(farm)
    await db.commit()
    await db.refresh(farm)
    return farm


@router.put("/farms/{farm_id}", response_model=FarmResponse)
async def update_farm(
    farm_id: int,
    payload: FarmCreatePayload,
    current_user: User = Depends(require_role("farmer", "admin")),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Farm).where(Farm.id == farm_id)
    farm = (await db.execute(stmt)).scalar_one_or_none()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

    # Security check: Farmers can only edit their own farms!
    if farm.farmer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to access this farm")

    computed_stage = await calculate_crop_stage(db, payload.crop_id, payload.sowing_date)

    farm.crop_id = payload.crop_id
    farm.sowing_date = payload.sowing_date
    farm.area_acres = payload.area_acres
    farm.soil_type = payload.soil_type
    farm.current_stage = computed_stage
    farm.irrigation_type = payload.irrigation_type
    farm.irrigation_type_note = payload.irrigation_type_note

    await db.commit()
    await db.refresh(farm)
    return farm


@router.delete("/farms/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_farm(
    farm_id: int,
    current_user: User = Depends(require_role("farmer", "admin")),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Farm).where(Farm.id == farm_id)
    farm = (await db.execute(stmt)).scalar_one_or_none()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

    if farm.farmer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to delete this farm")

    await db.delete(farm)
    await db.commit()


@router.get("/farms/{farm_id}/soil-test", response_model=List[SoilTestResponse])
async def list_soil_tests(
    farm_id: int,
    current_user: User = Depends(require_role("farmer", "admin")),
    db: AsyncSession = Depends(get_db)
):
    stmt_farm = select(Farm).where(Farm.id == farm_id)
    farm = (await db.execute(stmt_farm)).scalar_one_or_none()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

    if farm.farmer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to access this farm's soil tests")

    stmt = select(SoilTest).where(SoilTest.farm_id == farm_id).order_by(SoilTest.tested_on.desc())
    soil_tests = (await db.execute(stmt)).scalars().all()
    return soil_tests


@router.post("/farms/{farm_id}/soil-test", response_model=SoilTestResponse, status_code=status.HTTP_201_CREATED)
async def create_soil_test(
    farm_id: int,
    payload: SoilTestPayload,
    current_user: User = Depends(require_role("farmer", "admin")),
    db: AsyncSession = Depends(get_db)
):
    stmt_farm = select(Farm).where(Farm.id == farm_id)
    farm = (await db.execute(stmt_farm)).scalar_one_or_none()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

    if farm.farmer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to add soil tests to this farm")

    soil_test = SoilTest(
        farm_id=farm_id,
        ph=payload.ph,
        nitrogen=payload.nitrogen,
        phosphorus=payload.phosphorus,
        potassium=payload.potassium,
        organic_carbon=payload.organic_carbon,
        tested_on=payload.tested_on
    )
    db.add(soil_test)
    await db.commit()
    await db.refresh(soil_test)
    return soil_test
