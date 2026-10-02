from datetime import date, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_role
from app.core.database import get_db
from app.models import BookingGroup, Crop, CropMachineMap, Farm, FarmerProfile, Machine, User
from app.services.machinery_plan import machinery_plan
from app.api.v1.endpoints.resources import coordinates_from_location, point_from_lat_lng

router = APIRouter()
IST = ZoneInfo("Asia/Kolkata")


async def _farm_for_owner(db: AsyncSession, farm_id: int, user_id: int):
    statement = select(Farm).where(Farm.id == farm_id).options(selectinload(Farm.crop).selectinload(Crop.machine_mappings).selectinload(CropMachineMap.stage), selectinload(Farm.crop).selectinload(Crop.machine_mappings).selectinload(CropMachineMap.machine_type), selectinload(Farm.farmer).selectinload(User.farmer_profile))
    farm = (await db.execute(statement)).scalar_one_or_none()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    if farm.farmer_id != user_id:
        raise HTTPException(status_code=403, detail="You are not authorized to access this farm")
    return farm


async def _demand_counts(db: AsyncSession, farm: Farm, items: list[dict], radius_km: float):
    profile = farm.farmer.farmer_profile
    origin = coordinates_from_location(profile.location) if profile and profile.location else None
    if not origin:
        return [(0, 0) for _ in items]
    origin_point = point_from_lat_lng(origin["lat"], origin["lng"])
    candidate_statement = (
        select(Farm)
        .join(FarmerProfile, FarmerProfile.user_id == Farm.farmer_id)
        .where(Farm.id != farm.id, func.ST_DWithin(FarmerProfile.location, origin_point, radius_km * 1000))
        .options(
            selectinload(Farm.crop).selectinload(Crop.machine_mappings).selectinload(CropMachineMap.stage),
            selectinload(Farm.crop).selectinload(Crop.machine_mappings).selectinload(CropMachineMap.machine_type),
        )
    )
    candidates = (await db.execute(candidate_statement)).scalars().unique().all()
    results = []
    for item in items:
        start, end = item["needed_between"]
        demand_count = 0
        for candidate in candidates:
            overlaps = False
            for mapping in candidate.crop.machine_mappings:
                if mapping.machine_type_id != item["machine_type_id"]:
                    continue
                candidate_start = candidate.sowing_date + timedelta(days=mapping.stage.start_day + mapping.days_offset)
                candidate_end = candidate_start + timedelta(days=mapping.window_days)
                overlaps = candidate_start <= end and start <= candidate_end
                if overlaps:
                    break
            demand_count += int(overlaps)
        group_count = (
            await db.execute(
                select(func.count(BookingGroup.id))
                .join(Machine, BookingGroup.machine_id == Machine.id)
                .where(
                    BookingGroup.status == "open",
                    Machine.machine_type_id == item["machine_type_id"],
                    BookingGroup.scheduled_date >= start,
                    BookingGroup.scheduled_date <= end,
                )
            )
        ).scalar_one()
        results.append((demand_count, group_count))
    return results


@router.get("/farms/{farm_id}/machinery-plan")
async def get_machinery_plan(
    farm_id: int,
    sowing_date: Optional[date] = None,
    crop_id: Optional[int] = None,
    area_acres: Optional[float] = Query(None, gt=0),
    current_user: User = Depends(require_role("farmer")),
    db: AsyncSession = Depends(get_db),
):
    farm = await _farm_for_owner(db, farm_id, current_user.id)
    selected_crop = farm.crop
    if crop_id is not None and crop_id != farm.crop_id:
        selected_crop = (await db.execute(select(Crop).where(Crop.id == crop_id).options(selectinload(Crop.machine_mappings).selectinload(CropMachineMap.stage), selectinload(Crop.machine_mappings).selectinload(CropMachineMap.machine_type)))).scalar_one_or_none()
        if not selected_crop:
            raise HTTPException(status_code=404, detail="Crop not found")
    effective_sowing = sowing_date or farm.sowing_date
    effective_area = area_acres or farm.area_acres
    items = machinery_plan(selected_crop.machine_mappings, effective_sowing, effective_area)
    counts = await _demand_counts(db, farm, items, 10)
    for item, (demand, groups) in zip(items, counts):
        item["nearby_demand_count"] = demand
        item["open_groups_count"] = groups
        item["needed_between"] = [value.isoformat() for value in item["needed_between"]]
    next_needed = next((item for item in items if item["status"] != "passed"), None)
    return {
        "farm_summary": {"id": farm.id, "crop_id": selected_crop.id, "crop_name": selected_crop.name, "sowing_date": effective_sowing, "area_acres": effective_area},
        "items": items,
        "next_needed": next_needed,
        "overrides_applied": {"sowing_date": sowing_date is not None, "crop_id": crop_id is not None, "area_acres": area_acres is not None},
    }
