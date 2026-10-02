from datetime import date, timedelta
from types import SimpleNamespace

from app.services.advisory import (
    SOURCE,
    _llm_output_is_safe,
    calculate_stage,
    match_rules,
    rate_soil,
)


STAGES = [
    SimpleNamespace(stage_name="germination", start_day=0, end_day=10),
    SimpleNamespace(stage_name="tillering", start_day=11, end_day=25),
    SimpleNamespace(stage_name="flowering", start_day=26, end_day=40),
]


def test_stage_boundaries_and_after_harvest():
    assert calculate_stage(0, STAGES).current.stage_name == "germination"
    assert calculate_stage(11, STAGES).current.stage_name == "tillering"
    result = calculate_stage(41, STAGES)
    assert result.current.stage_name == "flowering"
    assert result.next_stage is None


def test_soil_and_rules_are_deterministic():
    soil = {"ph": 6.5, "nitrogen": 200, "phosphorus": 30, "potassium": 180, "organic_carbon": 0.6}
    ratings = rate_soil(soil)
    rule = SimpleNamespace(
        id=1,
        nutrient="nitrogen",
        condition_json={"nutrient": "nitrogen", "level": ["low"], "stage": "germination"},
        guidance_text="Use locally approved nitrogen guidance.",
        input_category="Fertilizer",
        source=SOURCE,
    )
    first = match_rules([rule], STAGES[0], STAGES[1], ratings, days_since_sowing_value=3)
    second = match_rules([rule], STAGES[0], STAGES[1], ratings, days_since_sowing_value=3)
    assert first == second


def test_recent_application_suppresses_suggestion():
    rule = SimpleNamespace(
        id=1,
        nutrient="nitrogen",
        condition_json={"nutrient": "nitrogen", "level": ["low"], "stage": "germination"},
        guidance_text="Use locally approved nitrogen guidance.",
        input_category="Fertilizer",
        source=SOURCE,
    )
    history = [SimpleNamespace(product_category="Fertilizer", applied_on=date.today() - timedelta(days=5))]
    result = match_rules([rule], STAGES[0], STAGES[1], rate_soil({"nitrogen": 200}), history)
    assert result[0]["status"] == "recently_applied"


def test_llm_guard_rejects_invented_number():
    assert not _llm_output_is_safe("Apply 99 kg now.", "Apply 60 kg now.")
    assert _llm_output_is_safe("Apply 60 kg now.", "Apply 60 kg now.")


def test_missing_soil_has_no_invented_levels():
    assert rate_soil(None) == {}
