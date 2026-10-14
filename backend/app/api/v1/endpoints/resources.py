from datetime import date
from typing import Any, Optional
import re
import struct

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2 import Geography
from pydantic import BaseModel, Field
from sqlalchemy import cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models import (
    BookingGroup,
    GroupMember,
    InputSeller,
    Machine,
    MachineType,
    Provider,
    User,
    FarmerProfile,
)

router = APIRouter()


class MachineListingPayload(BaseModel):
    machine_type: str = Field(min_length=2, max_length=100)
    rate_per_acre: float = Field(gt=0)
    available_from: date
    available_to: date
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


@router.post("/resources/machines", status_code=status.HTTP_201_CREATED)
async def create_machine_listing(
    payload: MachineListingPayload,
    current_user: User = Depends(require_role("provider", "admin")),
    db: AsyncSession = Depends(get_db),
):
    if payload.available_to < payload.available_from:
        raise HTTPException(status_code=422, detail="Availability end date must be after start date")
    provider = (await db.execute(select(Provider).where(Provider.user_id == current_user.id))).scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=403, detail="Only registered providers can list machinery")
    machine_type = (await db.execute(select(MachineType).where(MachineType.name.ilike(payload.machine_type)))).scalar_one_or_none()
    if not machine_type:
        raise HTTPException(status_code=404, detail="Machine type not found")
    machine = Machine(
        provider_id=current_user.id,
        machine_type_id=machine_type.id,
        location=f"POINT({payload.longitude} {payload.latitude})",
        rate_per_acre=payload.rate_per_acre,
        available_from=payload.available_from,
        available_to=payload.available_to,
        verified=False,
    )
    db.add(machine)
    await db.commit()
    await db.refresh(machine)
    return {"id": machine.id, "status": "pending_verification", "message": "Machine listing submitted for verification"}


def point_from_lat_lng(lat: float, lng: float):
    """Create a PostGIS geography point; PostGIS point order is longitude, latitude."""
    return cast(func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326), Geography)


def coordinates_from_location(location: Any) -> Optional[dict[str, float]]:
    """Convert stored POINT(lng lat) text/WKT into the API's {lat, lng} shape."""
    if location is None:
        return None
    if isinstance(location, bytes):
        location = location.decode("utf-8", errors="ignore")
    if hasattr(location, "data"):
        raw = location.data
        if isinstance(raw, bytes) and len(raw) >= 21:
            byte_order = "<" if raw[0] == 1 else ">"
            geometry_type = struct.unpack(f"{byte_order}I", raw[1:5])[0] & 0xFF
            if geometry_type == 1:
                lng, lat = struct.unpack(f"{byte_order}dd", raw[5:21])
                return {"lat": lat, "lng": lng}
    match = re.search(r"POINT\s*\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s*\)", str(location), re.I)
    if not match:
        return None
    lng, lat = map(float, match.groups())
    return {"lat": lat, "lng": lng}


def validate_radius(radius_km: float) -> float:
    if not 1 <= radius_km <= 100:
        raise HTTPException(status_code=422, detail="radius_km must be between 1 and 100")
    return radius_km * 1000


def is_machine_available(machine: Any, requested_date: Optional[date], confirmed_acres: float = 0, capacity: Optional[float] = None) -> bool:
    if requested_date is None:
        return True
    if not machine.available_from <= requested_date <= machine.available_to:
        return False
    return capacity is None or confirmed_acres < capacity


async def resolve_origin(lat: Optional[float], lng: Optional[float], user: User, db: AsyncSession):
    if (lat is None) != (lng is None):
        raise HTTPException(status_code=422, detail="lat and lng must be provided together")
    if lat is not None:
        return lat, lng
    profile = (await db.execute(select(FarmerProfile).where(FarmerProfile.user_id == user.id))).scalar_one_or_none()
    location = profile.location if profile else None
    coordinates = coordinates_from_location(location)
    if not coordinates:
        raise HTTPException(status_code=422, detail="Provide lat/lng or save a farm location first")
    return coordinates["lat"], coordinates["lng"]


async def _machine_query(
    db: AsyncSession,
    user: User,
    lat: Optional[float],
    lng: Optional[float],
    radius_km: float,
    machine_type: Optional[str],
    requested_date: Optional[date],
    max_price: Optional[float],
    verified_only: bool,
    sort: str,
    page: int,
    page_size: int,
):
    origin_lat, origin_lng = await resolve_origin(lat, lng, user, db)
    radius_m = validate_radius(radius_km)
    origin = point_from_lat_lng(origin_lat, origin_lng)
    distance = func.ST_Distance(Machine.location, origin).label("distance_m")

    statement = (
        select(Machine, MachineType, Provider, User, distance)
        .join(MachineType, Machine.machine_type_id == MachineType.id)
        .join(Provider, Machine.provider_id == Provider.user_id)
        .join(User, Provider.user_id == User.id)
        .where(func.ST_DWithin(Machine.location, origin, radius_m))
    )
    if verified_only:
        statement = statement.where(Machine.verified.is_(True))
    if machine_type:
        statement = statement.where(MachineType.name.ilike(f"%{machine_type}%"))
    if requested_date:
        statement = statement.where(Machine.available_from <= requested_date, Machine.available_to >= requested_date)
        occupied_acres = (
            select(func.coalesce(func.sum(GroupMember.acres), 0))
            .where(GroupMember.group_id == BookingGroup.id, GroupMember.status != "cancelled")
            .correlate(BookingGroup)
            .scalar_subquery()
        )
        fully_booked = select(BookingGroup.id).where(
            BookingGroup.machine_id == Machine.id,
            BookingGroup.scheduled_date == requested_date,
            BookingGroup.status == "confirmed",
            occupied_acres >= BookingGroup.max_acres,
        ).exists()
        statement = statement.where(~fully_booked)
    if max_price is not None:
        statement = statement.where(Machine.rate_per_acre <= max_price)

    if sort == "distance":
        statement = statement.order_by(distance)
    elif sort == "rating":
        statement = statement.order_by(Machine.rating.desc(), distance)
    elif sort == "price":
        statement = statement.order_by(Machine.rate_per_acre, distance)
    elif sort == "availability":
        statement = statement.order_by(Machine.available_from, distance)
    else:
        raise HTTPException(status_code=422, detail="sort must be distance, rating, price, or availability")

    statement = statement.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(statement)).all()
    results = []
    for machine, machine_type_obj, provider, provider_user, distance_m in rows:
        results.append({
            "id": machine.id,
            "resource_type": "machine",
            "machine_type": {"name": machine_type_obj.name, "name_hi": machine_type_obj.name_hi, "name_mr": machine_type_obj.name_mr},
            "provider": {"name": provider_user.name, "org_type": provider.org_type, "verified": bool(provider.verified)},
            "rate_per_acre": machine.rate_per_acre,
            "mobilization_cost": machine.mobilization_cost,
            "available_from": machine.available_from,
            "available_to": machine.available_to,
            "rating": machine.rating,
            "verified": bool(machine.verified),
            "photos": machine.photos or [],
            "description": machine.description,
            "model_year": machine.model_year,
            "specifications": machine.specifications or {},
            "distance_km": round(float(distance_m) / 1000, 2),
            "coordinates": coordinates_from_location(machine.location),
        })
    return results, (origin_lat, origin_lng)


@router.get("/resources/machines")
async def list_machines(
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lng: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: float = Query(10, ge=1, le=100),
    type: Optional[str] = None,
    date: Optional[date] = None,
    max_price: Optional[float] = Query(None, ge=0),
    verified_only: bool = False,  # Stage A: show unverified too (with badge)
    sort: str = "distance",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_role("farmer", "admin")),
    db: AsyncSession = Depends(get_db),
):
    results, origin = await _machine_query(db, current_user, lat, lng, radius_km, type, date, max_price, verified_only, sort, page, page_size)
    return {"items": results, "page": page, "page_size": page_size, "origin": {"lat": origin[0], "lng": origin[1]}}


@router.get("/resources/machine-types")
async def list_machine_types(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(MachineType).order_by(MachineType.name))).scalars().all()
    return [
        {"id": item.id, "name": item.name, "name_hi": item.name_hi, "name_mr": item.name_mr}
        for item in rows
    ]


@router.get("/resources/providers")
async def list_providers(
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lng: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: float = Query(10, ge=1, le=100),
    org_type: Optional[str] = None,
    verified_only: bool = True,
    current_user: User = Depends(require_role("farmer", "admin")),
    db: AsyncSession = Depends(get_db),
):
    origin_lat, origin_lng = await resolve_origin(lat, lng, current_user, db)
    origin = point_from_lat_lng(origin_lat, origin_lng)
    distance = func.ST_Distance(Machine.location, origin)
    statement = select(Provider, User, Machine, distance.label("distance_m")).join(User, Provider.user_id == User.id).join(Machine, Machine.provider_id == Provider.user_id).where(func.ST_DWithin(Machine.location, origin, validate_radius(radius_km)))
    if verified_only:
        statement = statement.where(Provider.verified.is_(True))
    if org_type:
        statement = statement.where(Provider.org_type == org_type)
    rows = (await db.execute(statement)).all()
    unique = {}
    for provider, provider_user, machine, distance_m in rows:
        unique[provider.user_id] = {"id": provider.user_id, "resource_type": "provider", "name": provider_user.name, "org_type": provider.org_type, "verified": bool(provider.verified), "distance_km": round(float(distance_m) / 1000, 2), "coordinates": coordinates_from_location(machine.location)}
    return {"items": list(unique.values()), "origin": {"lat": origin_lat, "lng": origin_lng}}


@router.get("/resources/input-sellers")
async def list_input_sellers(
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lng: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: float = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    verified_only: bool = True,
    current_user: User = Depends(require_role("farmer", "admin")),
    db: AsyncSession = Depends(get_db),
):
    origin_lat, origin_lng = await resolve_origin(lat, lng, current_user, db)
    origin = point_from_lat_lng(origin_lat, origin_lng)
    distance = func.ST_Distance(InputSeller.location, origin).label("distance_m")
    statement = select(InputSeller, distance).where(func.ST_DWithin(InputSeller.location, origin, validate_radius(radius_km)))
    if verified_only:
        statement = statement.where(InputSeller.verified.is_(True))
    if category:
        statement = statement.where(InputSeller.categories.contains([category]))
    rows = (await db.execute(statement)).all()
    return {"items": [{"id": seller.id, "resource_type": "input_seller", "name": seller.name, "verified": bool(seller.verified), "categories": seller.categories, "distance_km": round(float(distance_m) / 1000, 2), "coordinates": coordinates_from_location(seller.location)} for seller, distance_m in rows], "origin": {"lat": origin_lat, "lng": origin_lng}}


@router.get("/resources/machines/{machine_id}")
async def machine_detail(
    machine_id: int,
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lng: Optional[float] = Query(None, ge=-180, le=180),
    current_user: User = Depends(require_role("farmer", "admin")),
    db: AsyncSession = Depends(get_db),
):
    origin_lat, origin_lng = await resolve_origin(lat, lng, current_user, db)
    origin = point_from_lat_lng(origin_lat, origin_lng)
    distance = func.ST_Distance(Machine.location, origin).label("distance_m")
    statement = select(Machine, MachineType, Provider, User, distance).join(MachineType).join(Provider).join(User).where(Machine.id == machine_id)
    row = (await db.execute(statement)).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Machine not found")
    machine, machine_type_obj, provider, provider_user, distance_m = row
    groups = (await db.execute(select(BookingGroup).where(BookingGroup.machine_id == machine_id, BookingGroup.status == "open", BookingGroup.scheduled_date >= date.today()).order_by(BookingGroup.scheduled_date))).scalars().all()
    return {
        "id": machine.id,
        "resource_type": "machine",
        "machine_type": {"name": machine_type_obj.name, "name_hi": machine_type_obj.name_hi, "name_mr": machine_type_obj.name_mr},
        "provider": {"name": provider_user.name, "phone": provider_user.phone, "org_type": provider.org_type, "verified": bool(provider.verified)},
        "rate_per_acre": machine.rate_per_acre,
        "mobilization_cost": machine.mobilization_cost,
        "available_from": machine.available_from,
        "available_to": machine.available_to,
        "rating": machine.rating,
        "verified": bool(machine.verified),
        "photos": machine.photos or [],
        "description": machine.description,
        "model_year": machine.model_year,
        "specifications": machine.specifications or {},
        "distance_km": round(float(distance_m) / 1000, 2),
        "coordinates": coordinates_from_location(machine.location),
        "upcoming_open_groups": [{"id": group.id, "date": group.scheduled_date, "max_acres": group.max_acres} for group in groups],
    }
