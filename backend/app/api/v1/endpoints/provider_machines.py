"""
Provider machine management endpoints.

All routes require role=provider (or admin).  A provider can only view/edit/delete
their own machines — any attempt to touch another provider's machine returns 403.

Routes:
  POST   /provider/machines           — create a new machine listing
  GET    /provider/machines/mine      — list the calling provider's machines
  PUT    /provider/machines/{id}      — update own machine
  DELETE /provider/machines/{id}      — delete own machine
"""
import logging
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models.machine import Machine, MachineType
from app.models.user import Provider, User

router = APIRouter(prefix="/provider", tags=["provider"])
logger = logging.getLogger(__name__)


# ─── Pydantic schemas ────────────────────────────────────────────────────────


class MachineCreatePayload(BaseModel):
    machine_type_id: int
    rate_per_acre: float = Field(gt=0)
    mobilization_cost: float = Field(default=0.0, ge=0)
    available_from: date
    available_to: date
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    description: Optional[str] = Field(None, max_length=1000)
    model_year: Optional[int] = Field(None, ge=1950, le=2100)
    specifications: Optional[Dict[str, Any]] = None
    photo_urls: Optional[List[str]] = Field(default_factory=list)


class MachineUpdatePayload(BaseModel):
    rate_per_acre: Optional[float] = Field(None, gt=0)
    mobilization_cost: Optional[float] = Field(None, ge=0)
    available_from: Optional[date] = None
    available_to: Optional[date] = None
    description: Optional[str] = Field(None, max_length=1000)
    model_year: Optional[int] = Field(None, ge=1950, le=2100)
    specifications: Optional[Dict[str, Any]] = None
    photo_urls: Optional[List[str]] = None


def _machine_to_dict(machine: Machine) -> dict:
    return {
        "id": machine.id,
        "machine_type_id": machine.machine_type_id,
        "rate_per_acre": machine.rate_per_acre,
        "mobilization_cost": machine.mobilization_cost,
        "available_from": machine.available_from,
        "available_to": machine.available_to,
        "verified": machine.verified,
        "rating": machine.rating,
        "photos": machine.photos or [],
        "description": machine.description,
        "model_year": machine.model_year,
        "specifications": machine.specifications or {},
        "location": f"POINT({machine.location})" if machine.location else None,
    }


async def _get_provider_or_403(user: User, db: AsyncSession) -> Provider:
    provider = (
        await db.execute(select(Provider).where(Provider.user_id == user.id))
    ).scalar_one_or_none()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only registered providers can perform this action.",
        )
    return provider


async def _get_own_machine_or_403(machine_id: int, provider: Provider, db: AsyncSession) -> Machine:
    machine = (
        await db.execute(select(Machine).where(Machine.id == machine_id))
    ).scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found.")
    if machine.provider_id != provider.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this machine listing.",
        )
    return machine


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post(
    "/machines",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new machine listing (provider only)",
)
async def create_machine(
    payload: MachineCreatePayload,
    current_user: User = Depends(require_role("provider", "admin")),
    db: AsyncSession = Depends(get_db),
):
    provider = await _get_provider_or_403(current_user, db)

    if payload.available_to < payload.available_from:
        raise HTTPException(status_code=422, detail="available_to must be on or after available_from.")

    machine_type = (
        await db.execute(select(MachineType).where(MachineType.id == payload.machine_type_id))
    ).scalar_one_or_none()
    if not machine_type:
        raise HTTPException(status_code=404, detail="Machine type not found.")

    machine = Machine(
        provider_id=provider.user_id,
        machine_type_id=machine_type.id,
        location=f"POINT({payload.longitude} {payload.latitude})",
        rate_per_acre=payload.rate_per_acre,
        mobilization_cost=payload.mobilization_cost,
        available_from=payload.available_from,
        available_to=payload.available_to,
        verified=False,
        photos=payload.photo_urls or [],
        description=payload.description,
        model_year=payload.model_year,
        specifications=payload.specifications or {},
    )
    db.add(machine)
    await db.commit()
    await db.refresh(machine)

    return {
        "id": machine.id,
        "machine_type": machine_type.name,
        "status": "pending_verification",
        "message": "Machine listing created. It will appear on the farmer map once verified.",
        **_machine_to_dict(machine),
    }


@router.get(
    "/machines/mine",
    status_code=status.HTTP_200_OK,
    summary="List the calling provider's own machines",
)
async def list_my_machines(
    current_user: User = Depends(require_role("provider", "admin")),
    db: AsyncSession = Depends(get_db),
):
    provider = await _get_provider_or_403(current_user, db)

    rows = (
        await db.execute(
            select(Machine, MachineType)
            .join(MachineType, Machine.machine_type_id == MachineType.id)
            .where(Machine.provider_id == provider.user_id)
            .order_by(Machine.id.desc())
        )
    ).all()

    items = []
    for machine, machine_type in rows:
        item = _machine_to_dict(machine)
        item["machine_type"] = {
            "id": machine_type.id,
            "name": machine_type.name,
            "name_hi": machine_type.name_hi,
            "name_mr": machine_type.name_mr,
        }
        items.append(item)

    return {"items": items, "total": len(items)}


@router.put(
    "/machines/{machine_id}",
    status_code=status.HTTP_200_OK,
    summary="Update own machine listing",
)
async def update_machine(
    machine_id: int,
    payload: MachineUpdatePayload,
    current_user: User = Depends(require_role("provider", "admin")),
    db: AsyncSession = Depends(get_db),
):
    provider = await _get_provider_or_403(current_user, db)
    machine = await _get_own_machine_or_403(machine_id, provider, db)

    # Apply only the fields that were explicitly sent
    if payload.rate_per_acre is not None:
        machine.rate_per_acre = payload.rate_per_acre
    if payload.mobilization_cost is not None:
        machine.mobilization_cost = payload.mobilization_cost
    if payload.available_from is not None:
        machine.available_from = payload.available_from
    if payload.available_to is not None:
        machine.available_to = payload.available_to
    if payload.description is not None:
        machine.description = payload.description
    if payload.model_year is not None:
        machine.model_year = payload.model_year
    if payload.specifications is not None:
        machine.specifications = payload.specifications
    if payload.photo_urls is not None:
        machine.photos = payload.photo_urls

    # Validate date range after possible updates
    if machine.available_to < machine.available_from:
        raise HTTPException(status_code=422, detail="available_to must be on or after available_from.")

    await db.commit()
    await db.refresh(machine)
    return {"message": "Machine updated successfully.", **_machine_to_dict(machine)}


@router.delete(
    "/machines/{machine_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete own machine listing",
)
async def delete_machine(
    machine_id: int,
    current_user: User = Depends(require_role("provider", "admin")),
    db: AsyncSession = Depends(get_db),
):
    provider = await _get_provider_or_403(current_user, db)
    machine = await _get_own_machine_or_403(machine_id, provider, db)
    await db.delete(machine)
    await db.commit()
    return {"message": f"Machine {machine_id} deleted successfully."}
