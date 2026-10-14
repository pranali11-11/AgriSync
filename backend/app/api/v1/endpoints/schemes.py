from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import date, datetime, timedelta

from app.core.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.crop import Crop
from app.models.farm import Farm
from app.models.notification import Notification
from app.models.scheme import Scheme, SchemeNotificationPreference
from app.models.user import FarmerProfile, User
from app.services.scheme_notifications import create_due_scheme_notifications

router = APIRouter()


class SchemeListItem(BaseModel):
    id: int
    name: str
    name_hi: Optional[str]
    name_mr: Optional[str]
    level: str
    department: str
    short_description: str
    short_description_hi: Optional[str] = None
    short_description_mr: Optional[str] = None
    deadline: Optional[date] = None
    status: str
    notify_enabled: bool = False

    model_config = ConfigDict(from_attributes=True)


class SchemeWrite(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    name_hi: Optional[str] = None
    name_mr: Optional[str] = None
    level: str = Field(..., pattern="^(central|state)$")
    department: str = Field(..., min_length=1, max_length=255)
    short_description: str = Field(..., min_length=1)
    short_description_hi: Optional[str] = None
    short_description_mr: Optional[str] = None
    eligibility_text: str
    benefits_text: str
    required_documents: List[str] = Field(default_factory=list)
    application_process_text: str
    official_link: str = Field(..., pattern="^https?://")
    deadline: Optional[date] = None
    status: str = Field(default="active", pattern="^(active|upcoming|closed)$")
    crops: List[str] = Field(default_factory=list)
    states: List[str] = Field(default_factory=list)
    last_verified_on: datetime
    source: str


class SchemeDetail(SchemeWrite):
    id: int
    notify_enabled: bool = False

    model_config = ConfigDict(from_attributes=True)


class NotifyPreferenceUpdate(BaseModel):
    enabled: bool


@router.get("", response_model=List[SchemeListItem])
@router.get("/", response_model=List[SchemeListItem])
async def list_schemes(
    crop: Optional[str] = Query(None, description="Filter by crop name"),
    state: Optional[str] = Query(None, description="Filter by state"),
    status: Optional[str] = Query(None, description="Filter by status (active|upcoming|closed)"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    show_all: bool = Query(False, description="Disable farmer crop and state defaults"),
    deadline_soon: bool = Query(False, description="Only schemes with deadlines in the next 30 days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve government schemes with optional filtering by crop, state, status, and search."""
    crop = crop.strip() or None if crop is not None else None
    state = state.strip() or None if state is not None else None
    selected_crops = [crop] if crop else []
    selected_state = state

    if not show_all and current_user.role == "farmer":
        if crop is None:
            crop_stmt = select(Crop.name).join(Farm, Farm.crop_id == Crop.id).where(
                Farm.farmer_id == current_user.id
            )
            selected_crops = list((await db.execute(crop_stmt)).scalars().all())
        if state is None:
            state_stmt = select(FarmerProfile.state).where(
                FarmerProfile.user_id == current_user.id
            )
            selected_state = (await db.execute(state_stmt)).scalar_one_or_none()

    stmt = select(Scheme)
    if status:
        stmt = stmt.where(Scheme.status == status)
    stmt = stmt.order_by(Scheme.level, Scheme.name)
    schemes = list((await db.execute(stmt)).scalars().all())

    if selected_crops:
        wanted_crops = {value.strip().casefold() for value in selected_crops}
        schemes = [
            scheme for scheme in schemes
            if not scheme.crops
            or any(value.strip().casefold() in wanted_crops for value in scheme.crops)
        ]
    if selected_state:
        wanted_state = selected_state.strip().casefold()
        schemes = [
            scheme for scheme in schemes
            if not scheme.states
            or any(value.strip().casefold() == wanted_state for value in scheme.states)
        ]
    if search:
        term = search.strip().casefold()
        schemes = [
            scheme for scheme in schemes
            if term in scheme.name.casefold()
            or term in (scheme.name_hi or "").casefold()
            or term in (scheme.name_mr or "").casefold()
            or term in scheme.short_description.casefold()
            or term in (scheme.short_description_hi or "").casefold()
            or term in (scheme.short_description_mr or "").casefold()
        ]
    if deadline_soon:
        today = date.today()
        deadline_limit = today + timedelta(days=30)
        schemes = [
            scheme for scheme in schemes
            if scheme.deadline is not None and today <= scheme.deadline <= deadline_limit
        ]
    if current_user.role == "farmer":
        await create_due_scheme_notifications(db, current_user)
    preference_stmt = select(SchemeNotificationPreference.scheme_id).where(
        SchemeNotificationPreference.user_id == current_user.id
    )
    enabled_ids = set((await db.execute(preference_stmt)).scalars().all())
    return [
        SchemeListItem.model_validate(scheme).model_copy(
            update={"notify_enabled": scheme.id in enabled_ids}
        )
        for scheme in schemes
    ]


@router.get("/{scheme_id}", response_model=SchemeDetail)
async def get_scheme(
    scheme_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full details of a specific government scheme."""
    stmt = select(Scheme).where(Scheme.id == scheme_id)
    scheme = (await db.execute(stmt)).scalar_one_or_none()
    if not scheme:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Scheme not found")
    preference_stmt = select(SchemeNotificationPreference.id).where(
        SchemeNotificationPreference.user_id == current_user.id,
        SchemeNotificationPreference.scheme_id == scheme_id,
    )
    enabled = (await db.execute(preference_stmt)).scalar_one_or_none() is not None
    return SchemeDetail.model_validate(scheme).model_copy(update={"notify_enabled": enabled})


@router.post("", response_model=SchemeDetail, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=SchemeDetail, status_code=status.HTTP_201_CREATED)
async def create_scheme(
    payload: SchemeWrite,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    scheme = Scheme(**payload.model_dump())
    db.add(scheme)
    await db.commit()
    await db.refresh(scheme)
    return scheme


@router.put("/{scheme_id}", response_model=SchemeDetail)
async def update_scheme(
    scheme_id: int,
    payload: SchemeWrite,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    scheme = await db.get(Scheme, scheme_id)
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    for field, value in payload.model_dump().items():
        setattr(scheme, field, value)
    await db.commit()
    await db.refresh(scheme)
    return scheme


@router.delete("/{scheme_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheme(
    scheme_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    scheme = await db.get(Scheme, scheme_id)
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    await db.delete(scheme)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{scheme_id}/notify")
async def set_scheme_notification(
    scheme_id: int,
    payload: NotifyPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scheme = await db.get(Scheme, scheme_id)
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    if payload.enabled and (
        scheme.deadline is None or scheme.deadline <= date.today() or scheme.status == "closed"
    ):
        raise HTTPException(status_code=400, detail="Notifications require an upcoming deadline")

    preference_stmt = select(SchemeNotificationPreference).where(
        SchemeNotificationPreference.user_id == current_user.id,
        SchemeNotificationPreference.scheme_id == scheme_id,
    )
    preference = (await db.execute(preference_stmt)).scalar_one_or_none()
    if payload.enabled and preference is None:
        db.add(SchemeNotificationPreference(user_id=current_user.id, scheme_id=scheme_id))
    elif not payload.enabled and preference is not None:
        await db.delete(preference)
    await db.commit()
    return {"enabled": payload.enabled}
