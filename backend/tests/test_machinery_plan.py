from datetime import date, timedelta
from types import SimpleNamespace

from app.services.machinery_plan import machinery_plan


def mapping(stage_day, offset=0, window=5):
    return SimpleNamespace(
        machine_type_id=4,
        days_offset=offset,
        window_days=window,
        source="SAMPLE - verify with ICAR / state agriculture dept",
        stage=SimpleNamespace(stage_name="Sowing", start_day=stage_day),
        machine_type=SimpleNamespace(name="Seed Drill", name_hi="सीड ड्रिल", name_mr="बियाणे पेरणी यंत्र", typical_rate_per_acre=1000, mobilization_cost=1500),
    )


def test_dates_statuses_and_exact_costs():
    sowing = date(2026, 9, 1)
    today = date(2026, 9, 8)
    items = machinery_plan([mapping(0), mapping(7), mapping(20)], sowing, 2, today)
    assert items[0]["needed_between"] == [date(2026, 9, 1), date(2026, 9, 6)]
    assert items[0]["status"] == "passed"
    assert items[1]["status"] == "in_window"
    assert items[2]["status"] == "upcoming"
    assert items[0]["estimated_cost_solo"]["paise"] == 350000


def test_status_boundaries():
    today = date(2026, 9, 21)
    assert machinery_plan([mapping(7)], today, 1, today)[0]["status"] == "due_soon"
    assert machinery_plan([mapping(0, window=0)], today, 1, today)[0]["status"] == "in_window"
    assert machinery_plan([mapping(-2, window=0)], today, 1, today)[0]["status"] == "passed"


def test_area_doubles_machine_cost_not_mobilization():
    one = machinery_plan([mapping(0)], date(2026, 9, 1), 1, date(2026, 9, 1))[0]
    two = machinery_plan([mapping(0)], date(2026, 9, 1), 2, date(2026, 9, 1))[0]
    assert one["estimated_cost_solo"]["paise"] == 250000
    assert two["estimated_cost_solo"]["paise"] == 350000
