from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
import json
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.api.deps import get_current_user, require_role
from app.core.security import decode_jwt_token
from app.core.database import get_db
from app.models import BookingGroup, Farm, GroupMember, Machine, MachineType, Notification, Provider, User
from app.services.group_booking import calculate_group_costs, preview_member_cost

router = APIRouter()
CANCEL_DEADLINE_HOURS = 48


def _money(paise: int) -> float:
    return float(Decimal(paise) / 100)


def _deadline(group: BookingGroup) -> datetime:
    return datetime.combine(group.scheduled_date, datetime.min.time(), tzinfo=timezone.utc) - timedelta(hours=CANCEL_DEADLINE_HOURS)


def _member_rows(group: BookingGroup):
    return [
        {"id": member.id, "farmer_id": member.farmer_id, "farm_id": member.farm_id, "first_name": member.farmer.name.split()[0], "village": member.farm.farmer.farmer_profile.village if member.farm.farmer.farmer_profile else None, "acres": member.acres, "share_amount": member.share_amount}
        for member in group.members if member.status != "cancelled"
    ]


def _snapshot(group: BookingGroup):
    members = _member_rows(group)
    return {"id": group.id, "machine_id": group.machine_id, "name": group.name or f"{group.machine.machine_type.name} group", "description": group.description, "crop_focus": group.crop_focus, "radius_km": group.radius_km, "scheduled_date": group.scheduled_date, "status": group.status, "min_farmers": group.min_farmers, "max_acres": group.max_acres, "members": members, "member_count": len(members), "total_acres": sum(member["acres"] for member in members), "total_cost": sum(member["share_amount"] for member in members), "spots_left": max(0, group.min_farmers - len(members)), "acres_left": max(0, group.max_acres - sum(member["acres"] for member in members)), "cancel_deadline": _deadline(group)}


async def _group(db, group_id: int, lock: bool = False):
    if lock:
        # PostgreSQL rejects FOR UPDATE on queries that include outer joins from eager
        # relationship loading, so we lock only the BookingGroup row and let the
        # relationship data load lazily as needed for the guarded mutation path.
        statement = select(BookingGroup).where(BookingGroup.id == group_id).with_for_update(of=BookingGroup)
        return (await db.execute(statement)).scalar_one_or_none()

    statement = select(BookingGroup).where(BookingGroup.id == group_id).options(
        joinedload(BookingGroup.machine).joinedload(Machine.machine_type),
        joinedload(BookingGroup.machine).joinedload(Machine.provider).joinedload(Provider.user),
        selectinload(BookingGroup.members).joinedload(GroupMember.farmer).joinedload(User.farmer_profile),
        selectinload(BookingGroup.members).joinedload(GroupMember.farm).joinedload(Farm.farmer).joinedload(User.farmer_profile),
    )
    return (await db.execute(statement)).unique().scalar_one_or_none()


async def _farm_for_user(db, farm_id: int, user_id: int):
    farm = (await db.execute(select(Farm).where(Farm.id == farm_id))).scalar_one_or_none()
    if not farm or farm.farmer_id != user_id:
        raise HTTPException(status_code=403, detail="Farm does not belong to this farmer")
    return farm


async def _recalculate(group: BookingGroup):
    members = [member for member in group.members if member.status != "cancelled"]
    result = calculate_group_costs([member.acres for member in members], group.machine.rate_per_acre, group.machine.machine_type.mobilization_cost)
    for member, cost in zip(members, result["members"]):
        member.share_amount = _money(cost.share_paise)
    return result


async def _notify(db, user_ids, message):
    for user_id in set(user_ids):
        db.add(Notification(user_id=user_id, type="booking", message=message))


async def _assert_machine_available(db, machine: Machine, scheduled_date: date):
    if not machine.available_from <= scheduled_date <= machine.available_to:
        raise HTTPException(status_code=409, detail="Machine is not available on that date")
    clash = (await db.execute(select(BookingGroup).where(BookingGroup.machine_id == machine.id, BookingGroup.scheduled_date == scheduled_date, BookingGroup.status == "confirmed"))).scalar_one_or_none()
    if clash:
        raise HTTPException(status_code=409, detail="Machine already has a confirmed group on that date")


@router.post("/groups")
async def create_group(payload: dict, current_user: User = Depends(require_role("farmer")), db: AsyncSession = Depends(get_db)):
    scheduled_date = date.fromisoformat(payload["scheduled_date"])
    if scheduled_date <= date.today():
        raise HTTPException(status_code=422, detail="Scheduled date must be in the future")
    farm = await _farm_for_user(db, int(payload["farm_id"]), current_user.id)
    acres = float(payload["acres"])
    if acres <= 0 or acres > farm.area_acres:
        raise HTTPException(status_code=422, detail="Acres must be positive and within the farm area")
    machine = (await db.execute(select(Machine).options(joinedload(Machine.machine_type)).where(Machine.id == payload["machine_id"]))).scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    await _assert_machine_available(db, machine, scheduled_date)
    group = BookingGroup(machine_id=machine.id, scheduled_date=scheduled_date, min_farmers=int(payload.get("min_farmers", 2)), max_acres=float(payload.get("max_acres", 20)), created_by=current_user.id, name=payload.get("name"), description=payload.get("description"), crop_focus=payload.get("crop_focus"), radius_km=float(payload.get("radius_km", 10)))
    db.add(group)
    await db.flush()
    member = GroupMember(group_id=group.id, farmer_id=current_user.id, farm_id=farm.id, acres=acres, share_amount=0)
    db.add(member)
    await db.flush()
    await db.refresh(group, ["members", "machine"])
    if group.min_farmers == 1:
        group.status = "confirmed"
    await _recalculate(group)
    if group.status == "confirmed":
        await _notify(db, [current_user.id, machine.provider_id], f"Group {group.id} confirmed")
    await db.commit()
    return _snapshot(await _group(db, group.id))


@router.get("/groups/mine")
async def mine(current_user: User = Depends(require_role("farmer")), db: AsyncSession = Depends(get_db)):
    groups = (await db.execute(select(BookingGroup).join(GroupMember).where(GroupMember.farmer_id == current_user.id).options(selectinload(BookingGroup.members)))).scalars().unique().all()
    return [_snapshot(await _group(db, group.id)) for group in groups]


@router.get("/groups/nearby")
async def nearby_groups(
    lat: Optional[float] = Query(None, ge=-90, le=90), lng: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: float = Query(10, ge=1, le=100), machine_type: Optional[str] = None,
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    current_user: User = Depends(require_role("farmer")), db: AsyncSession = Depends(get_db),
):
    from app.api.v1.endpoints.resources import resolve_origin, point_from_lat_lng, coordinates_from_location
    origin_lat, origin_lng = await resolve_origin(lat, lng, current_user, db)
    origin = point_from_lat_lng(origin_lat, origin_lng)
    distance = func.ST_Distance(Machine.location, origin).label("distance_m")
    statement = select(BookingGroup, distance).join(Machine).join(MachineType).where(BookingGroup.status == "open", BookingGroup.created_by != current_user.id, func.ST_DWithin(Machine.location, origin, radius_km * 1000)).options(selectinload(BookingGroup.members), joinedload(BookingGroup.machine).joinedload(Machine.machine_type))
    if machine_type: statement = statement.where(MachineType.name.ilike(f"%{machine_type}%"))
    if date_from: statement = statement.where(BookingGroup.scheduled_date >= date_from)
    if date_to: statement = statement.where(BookingGroup.scheduled_date <= date_to)
    joined = select(GroupMember.group_id).where(GroupMember.farmer_id == current_user.id, GroupMember.status != "cancelled")
    statement = statement.where(~BookingGroup.id.in_(joined)).order_by(distance, BookingGroup.scheduled_date)
    rows = (await db.execute(statement)).unique().all()
    return [{**_snapshot(group), "distance_km": round(float(distance_m) / 1000, 2), "machine": {"type": group.machine.machine_type.name}, "coordinates": coordinates_from_location(group.machine.location)} for group, distance_m in rows]


@router.websocket("/ws/groups/{group_id}")
async def group_socket(websocket: WebSocket, group_id: int, token: str, db: AsyncSession = Depends(get_db)):
    payload = decode_jwt_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=1008)
        return
    group = await _group(db, group_id)
    if not group:
        await websocket.close(code=1008)
        return
    user_id = int(payload.get("user_id", 0))
    is_member = any(member.farmer_id == user_id and member.status != "cancelled" for member in group.members)
    if not is_member and group.status != "open":
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({"event": "snapshot", "group": _snapshot(await _group(db, group_id))})
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=25)
            except asyncio.TimeoutError:
                await websocket.send_json({"event": "heartbeat"})
    except WebSocketDisconnect:
        return


@router.get("/groups/{group_id}")
async def get_group(group_id: int, current_user: User = Depends(require_role("farmer")), db: AsyncSession = Depends(get_db)):
    group = await _group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    snapshot = _snapshot(group)
    snapshot["machine"] = {"id": group.machine.id, "type": group.machine.machine_type.name, "rate_per_acre": group.machine.rate_per_acre, "mobilization_cost": group.machine.machine_type.mobilization_cost, "provider": group.machine.provider.user.name, "provider_id": group.machine.provider_id}
    return snapshot


@router.get("/groups/{group_id}/preview")
async def preview(group_id: int, acres: float = Query(..., gt=0), current_user: User = Depends(require_role("farmer")), db: AsyncSession = Depends(get_db)):
    group = await _group(db, group_id)
    if not group or group.status != "open":
        raise HTTPException(status_code=409, detail="Group is not open")
    existing = [member.acres for member in group.members if member.status != "cancelled"]
    if sum(existing) + acres > group.max_acres:
        raise HTTPException(status_code=409, detail="Group does not have enough acres left")
    cost = preview_member_cost(acres, existing, group.machine.rate_per_acre, group.machine.machine_type.mobilization_cost)
    return {"share_amount": _money(cost.share_paise), "savings": _money(cost.savings_paise), "machine_cost": _money(int(Decimal(str(acres)) * int(Decimal(str(group.machine.rate_per_acre)) * 100))), "mobilization_share": _money(cost.share_paise - int(Decimal(str(acres)) * int(Decimal(str(group.machine.rate_per_acre)) * 100)))}


@router.post("/groups/{group_id}/join")
async def join(group_id: int, payload: dict, current_user: User = Depends(require_role("farmer")), db: AsyncSession = Depends(get_db)):
    group = await _group(db, group_id, lock=True)
    if not group or group.status != "open" or group.scheduled_date <= date.today():
        raise HTTPException(status_code=409, detail="This group is no longer open for joining")
    farm = await _farm_for_user(db, int(payload["farm_id"]), current_user.id)
    acres = float(payload["acres"])
    if acres <= 0 or acres > farm.area_acres:
        raise HTTPException(status_code=422, detail="Acres must be positive and within the farm area")
    if any(member.farmer_id == current_user.id and member.status != "cancelled" for member in group.members):
        raise HTTPException(status_code=409, detail="You have already joined this group")
    if sum(member.acres for member in group.members if member.status != "cancelled") + acres > group.max_acres:
        raise HTTPException(status_code=409, detail="Group is full")
    member = GroupMember(group_id=group.id, farmer_id=current_user.id, farm_id=farm.id, acres=acres, share_amount=0)
    db.add(member)
    await db.flush()
    await _recalculate(group)
    if len([item for item in group.members if item.status != "cancelled"]) >= group.min_farmers:
        group.status = "confirmed"
        await _notify(db, [group.created_by, current_user.id, group.machine.provider_id, *[item.farmer_id for item in group.members]], f"Group {group.id} confirmed")
    await db.commit()
    return _snapshot(await _group(db, group.id))


@router.post("/groups/{group_id}/leave")
async def leave(group_id: int, current_user: User = Depends(require_role("farmer")), db: AsyncSession = Depends(get_db)):
    group = await _group(db, group_id, lock=True)
    if not group or datetime.now(timezone.utc) >= _deadline(group):
        raise HTTPException(status_code=409, detail="The cancellation deadline has passed")
    member = next((item for item in group.members if item.farmer_id == current_user.id and item.status != "cancelled"), None)
    if not member:
        raise HTTPException(status_code=404, detail="You are not a member of this group")
    member.status = "cancelled"
    active = [item for item in group.members if item.status != "cancelled" and item.id != member.id]
    if not active:
        group.status = "cancelled"
    elif group.status == "confirmed" and len(active) < group.min_farmers:
        group.status = "open"
        await _notify(db, [item.farmer_id for item in active], f"Group {group.id} reopened because a member left")
    elif group.created_by == current_user.id:
        group.created_by = min(active, key=lambda item: item.id).farmer_id
    await _recalculate(group) if active else None
    await db.commit()
    return _snapshot(await _group(db, group.id))


@router.post("/groups/{group_id}/cancel")
async def cancel(group_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    group = await _group(db, group_id, lock=True)
    if not group or (group.created_by != current_user.id and group.machine.provider_id != current_user.id):
        raise HTTPException(status_code=403, detail="Only the creator or provider can cancel this group")
    group.status = "cancelled"
    await _notify(db, [group.created_by, *[item.farmer_id for item in group.members]], f"Group {group.id} cancelled")
    await db.commit()
    return _snapshot(await _group(db, group.id))


@router.post("/groups/{group_id}/accept")
async def accept(group_id: int, current_user: User = Depends(require_role("provider")), db: AsyncSession = Depends(get_db)):
    group = await _group(db, group_id, lock=True)
    if not group or group.machine.provider_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the machine provider can accept this group")
    group.status = "confirmed"
    await db.commit()
    return _snapshot(await _group(db, group.id))


@router.post("/groups/{group_id}/decline")
async def decline(group_id: int, current_user: User = Depends(require_role("provider")), db: AsyncSession = Depends(get_db)):
    group = await _group(db, group_id, lock=True)
    if not group or group.machine.provider_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the machine provider can decline this group")
    group.status = "cancelled"
    await db.commit()
    return _snapshot(await _group(db, group.id))
