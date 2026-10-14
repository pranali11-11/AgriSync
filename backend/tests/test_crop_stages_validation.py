"""Tests for crop stage contiguity, coverage, and descriptions."""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.crop import Crop
from app.services.crop_validation import validate_crop_stages_integrity


@pytest.mark.asyncio
async def test_all_seeded_crop_stages_are_contiguous_and_valid():
    """Verify all crops in DB have contiguous, non-overlapping stages covering day 0 to duration."""
    async with AsyncSessionLocal() as db:
        stmt = select(Crop).options(selectinload(Crop.stages)).order_by(Crop.id)
        crops = (await db.execute(stmt)).scalars().all()
        assert len(crops) >= 20, "Expected at least 20 seeded crops"

        errors = validate_crop_stages_integrity(crops)
        assert errors == [], f"Validation errors found: {errors}"


@pytest.mark.asyncio
async def test_wheat_stages_and_descriptions():
    """Verify wheat has all required stages with descriptions and source."""
    async with AsyncSessionLocal() as db:
        stmt = select(Crop).options(selectinload(Crop.stages)).where(Crop.name == "Wheat")
        wheat = (await db.execute(stmt)).scalar_one()

        stage_names = [s.stage_name for s in wheat.stages]
        expected_subset = ["Sowing", "Germination", "Tillering", "Jointing", "Flowering", "Grain Filling", "Maturity"]
        for expected in expected_subset:
            assert expected in stage_names, f"Missing {expected} in wheat stages"

        assert wheat.stages[0].start_day == 0
        assert wheat.stages[-1].end_day == wheat.duration_days == 120

        for stage in wheat.stages:
            assert stage.stage_description, f"Missing description on wheat stage {stage.stage_name}"
            assert len(stage.stage_description) > 30, f"Description too short on {stage.stage_name}"
            assert stage.source == "SAMPLE - verify with ICAR / state agriculture dept"


@pytest.mark.asyncio
async def test_crops_api_returns_stage_descriptions():
    """Verify crops API returns stage_description and source in JSON response."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/crops")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 20

        for crop in data:
            assert len(crop["stages"]) >= 4
            for stage in crop["stages"]:
                assert "stage_description" in stage
                assert stage["stage_description"] is not None
                assert "source" in stage
                assert stage["source"] == "SAMPLE - verify with ICAR / state agriculture dept"
