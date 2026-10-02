import pytest
from datetime import date
from pydantic import ValidationError
from sqlalchemy import select

from app.models.farm import Farm, IrrigationType
from app.schemas.farm import FarmCreate, validate_irrigation_input
from app.api.v1.endpoints.farmers import FarmCreatePayload
from app.services.advisory import match_rules
from types import SimpleNamespace


def test_irrigation_type_enum_members_and_aliases():
    """All 8 canonical types and legacy aliases must resolve properly."""
    expected = [
        "rainfed", "canal", "borewell", "well",
        "drip", "sprinkler", "pond_tank", "other"
    ]
    for exp in expected:
        assert IrrigationType(exp).value == exp

    # Legacy & case-insensitive aliases
    assert IrrigationType("pond/tank") == IrrigationType.pond_tank
    assert IrrigationType("pond / tank") == IrrigationType.pond_tank
    assert IrrigationType("Well") == IrrigationType.well
    assert IrrigationType("Canal") == IrrigationType.canal
    assert IrrigationType("Drip") == IrrigationType.drip
    assert IrrigationType("drip / sprinkler") == IrrigationType.drip
    assert IrrigationType("tank") == IrrigationType.pond_tank


def test_other_requires_free_text_note():
    """Acceptance Check 2: 'Other' requires free-text note."""
    # Fails when note is None or empty
    with pytest.raises(ValidationError) as exc:
        FarmCreatePayload(
            crop_id=1,
            sowing_date=date.today(),
            area_acres=2.5,
            irrigation_type="other",
            irrigation_type_note="",
        )
    assert "Free-text note is required when irrigation type is 'other'" in str(exc.value)

    with pytest.raises(ValidationError):
        FarmCreatePayload(
            crop_id=1,
            sowing_date=date.today(),
            area_acres=2.5,
            irrigation_type="other",
            irrigation_type_note=None,
        )

    # Succeeds with a valid note
    payload = FarmCreatePayload(
        crop_id=1,
        sowing_date=date.today(),
        area_acres=2.5,
        irrigation_type="other",
        irrigation_type_note="River lift scheme with tanker backup",
    )
    assert payload.irrigation_type == "other"
    assert payload.irrigation_type_note == "River lift scheme with tanker backup"


def test_all_canonical_irrigation_types_payload_save():
    """Acceptance Check 1: All irrigation types are selectable and saved correctly."""
    options = [
        ("rainfed", None),
        ("canal", None),
        ("borewell", None),
        ("well", None),
        ("drip", None),
        ("sprinkler", None),
        ("pond_tank", None),
        ("pond/tank", None),  # alias maps to pond_tank
        ("other", "Custom tanker system"),
    ]
    for itype, inote in options:
        payload = FarmCreatePayload(
            crop_id=1,
            sowing_date=date.today(),
            area_acres=3.0,
            irrigation_type=itype,
            irrigation_type_note=inote,
        )
        assert payload.irrigation_type in [t.value for t in IrrigationType]
        if itype in ("pond_tank", "pond/tank"):
            assert payload.irrigation_type == "pond_tank"
        if itype == "other":
            assert payload.irrigation_type_note == inote


def test_drip_fertigation_advisory_enhancement():
    """Drip irrigation attaches fertigation guidance note to fertilizer recommendations."""
    rule = SimpleNamespace(
        id=10,
        nutrient="nitrogen",
        condition_json={"stage": "vegetative"},
        guidance_text="Apply 50 kg Urea per acre.",
        input_category="Fertilizer",
        source="Test Source",
    )
    stage = SimpleNamespace(stage_name="vegetative", start_day=1, end_day=20)
    
    # Without drip
    res_normal = match_rules([rule], stage, None, {}, irrigation_type="canal")
    assert "Drip-fertigation note" not in res_normal[0]["guidance_text"]

    # With drip
    res_drip = match_rules([rule], stage, None, {}, irrigation_type="drip")
    assert "Drip-fertigation note" in res_drip[0]["guidance_text"]


def test_existing_farms_load_without_crashing():
    """Acceptance Check 3: Existing farms with legacy irrigation values still load cleanly."""
    from app.api.v1.endpoints.farmers import FarmResponse

    legacy_farms = [
        {"id": 1, "farmer_id": 10, "crop_id": 1, "sowing_date": date.today(), "area_acres": 2.0, "soil_type": "clay", "current_stage": "sowing", "irrigation_type": "Well", "irrigation_type_note": None},
        {"id": 2, "farmer_id": 10, "crop_id": 2, "sowing_date": date.today(), "area_acres": 5.0, "soil_type": "black", "current_stage": "flowering", "irrigation_type": "Canal", "irrigation_type_note": None},
        {"id": 3, "farmer_id": 10, "crop_id": 3, "sowing_date": date.today(), "area_acres": 1.5, "soil_type": "loam", "current_stage": "vegetative", "irrigation_type": "Drip", "irrigation_type_note": None},
        {"id": 4, "farmer_id": 10, "crop_id": 4, "sowing_date": date.today(), "area_acres": 4.0, "soil_type": None, "current_stage": None, "irrigation_type": None, "irrigation_type_note": None},
        {"id": 5, "farmer_id": 10, "crop_id": 5, "sowing_date": date.today(), "area_acres": 3.0, "soil_type": None, "current_stage": None, "irrigation_type": "drip / sprinkler", "irrigation_type_note": None},
    ]

    for data in legacy_farms:
        resp = FarmResponse.model_validate(data)
        assert resp.id == data["id"]
        assert resp.irrigation_type == data["irrigation_type"]

