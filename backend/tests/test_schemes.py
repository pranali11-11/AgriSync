from datetime import date, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_current_user, get_db
from app.api.v1.endpoints.schemes import list_schemes
from app.core.database import Base
from app.main import app
from app.models import Crop, Farm, FarmerProfile, Notification, Scheme, SchemeNotificationPreference, User


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def scheme_record(name, *, crops=None, states=None, status="active", deadline=None):
    return Scheme(
        name=name,
        level="central",
        department="Agriculture Department",
        short_description=f"Summary for {name}",
        eligibility_text="Check current official eligibility.",
        benefits_text="Check current official benefits.",
        required_documents=["Aadhaar"],
        application_process_text="Apply through the official portal.",
        official_link="https://example.gov.in/scheme",
        deadline=deadline,
        status=status,
        crops=crops or [],
        states=states or [],
        last_verified_on=datetime(2026, 10, 2),
        source="Verify current details on official portal before relying on this",
    )


@pytest.mark.asyncio
async def test_scheme_list_defaults_to_farmer_crop_and_state_and_can_show_all(db_session):
    farmer = User(name="Farmer", phone="9000000001", role="farmer", language="en")
    crop = Crop(name="Wheat", duration_days=120)
    db_session.add_all([farmer, crop])
    await db_session.flush()
    db_session.add_all([
        FarmerProfile(user_id=farmer.id, state="Maharashtra"),
        Farm(farmer_id=farmer.id, crop_id=crop.id, sowing_date=date.today(), area_acres=1),
        scheme_record("All farmers", crops=[], states=[]),
        scheme_record("Wheat Maharashtra", crops=["Wheat"], states=["Maharashtra"]),
        scheme_record("Rice Maharashtra", crops=["Rice"], states=["Maharashtra"]),
        scheme_record("Wheat Punjab", crops=["Wheat"], states=["Punjab"]),
    ])
    await db_session.commit()

    filtered = await list_schemes(
        crop="", state="", status=None, search=None, show_all=False,
        deadline_soon=False, db=db_session, current_user=farmer,
    )
    assert {item.name for item in filtered} == {"All farmers", "Wheat Maharashtra"}

    all_schemes = await list_schemes(
        crop=None, state=None, status=None, search=None, show_all=True,
        deadline_soon=False, db=db_session, current_user=farmer,
    )
    assert len(all_schemes) == 4


@pytest.mark.asyncio
async def test_scheme_search_status_and_deadline_filters(db_session):
    farmer = User(name="Farmer", phone="9000000002", role="farmer", language="en")
    db_session.add_all([
        farmer,
        scheme_record("PM Wheat Support", status="active", deadline=date.today() + timedelta(days=10)),
        scheme_record("PM Rice Support", status="closed", deadline=date.today() + timedelta(days=10)),
        scheme_record("Older Support", status="active", deadline=date.today() + timedelta(days=45)),
    ])
    await db_session.commit()

    results = await list_schemes(
        crop=None, state=None, status="active", search="wheat", show_all=True,
        deadline_soon=True, db=db_session, current_user=farmer,
    )
    assert [item.name for item in results] == ["PM Wheat Support"]


@pytest.mark.asyncio
async def test_scheme_crud_is_admin_only(db_session):
    admin = User(name="Admin", phone="9000000003", role="admin", language="en")
    db_session.add(admin)
    await db_session.commit()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: admin
    payload = {
        "name": "Test Scheme",
        "level": "central",
        "department": "Agriculture Department",
        "short_description": "A test scheme.",
        "eligibility_text": "Check eligibility.",
        "benefits_text": "Check benefits.",
        "required_documents": ["Aadhaar"],
        "application_process_text": "Apply online.",
        "official_link": "https://example.gov.in/scheme",
        "status": "active",
        "crops": [],
        "states": [],
        "last_verified_on": "2026-10-02T00:00:00",
        "source": "Verify current details on official portal before relying on this",
    }
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post("/api/v1/schemes", json=payload)
            assert created.status_code == 201, created.text
            scheme_id = created.json()["id"]

            changed_payload = {**payload, "name": "Updated Scheme"}
            updated = await client.put(f"/api/v1/schemes/{scheme_id}", json=changed_payload)
            assert updated.status_code == 200
            assert updated.json()["name"] == "Updated Scheme"

            admin.role = "farmer"
            forbidden = await client.delete(f"/api/v1/schemes/{scheme_id}")
            assert forbidden.status_code == 403

            admin.role = "admin"
            deleted = await client.delete(f"/api/v1/schemes/{scheme_id}")
            assert deleted.status_code == 204
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_scheme_reminder_opt_in_creates_one_due_notification(db_session):
    farmer = User(name="Farmer", phone="9000000004", role="farmer", language="en")
    scheme = scheme_record("Deadline Scheme", deadline=date.today() + timedelta(days=5))
    db_session.add_all([farmer, scheme])
    await db_session.commit()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: farmer
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            enabled = await client.put(
                f"/api/v1/schemes/{scheme.id}/notify",
                json={"enabled": True},
            )
            assert enabled.status_code == 200
            assert enabled.json() == {"enabled": True}

            detail = await client.get(f"/api/v1/schemes/{scheme.id}")
            assert detail.json()["notify_enabled"] is True

            await client.get("/api/v1/schemes")
            await client.get("/api/v1/schemes")
            notification_count = await db_session.scalar(
                select(func.count()).select_from(Notification)
            )
            assert notification_count == 1

            disabled = await client.put(
                f"/api/v1/schemes/{scheme.id}/notify",
                json={"enabled": False},
            )
            assert disabled.status_code == 200
            assert disabled.json() == {"enabled": False}
            preference_count = await db_session.scalar(
                select(func.count()).select_from(SchemeNotificationPreference)
            )
            assert preference_count == 0
    finally:
        app.dependency_overrides.clear()
