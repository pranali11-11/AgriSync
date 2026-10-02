"""Pure machinery planning calculations."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

from app.services.group_booking import calculate_group_costs

IST = ZoneInfo("Asia/Kolkata")
SOURCE = "SAMPLE - verify with ICAR / state agriculture dept"


def machinery_plan(mappings: Iterable[Any], sowing_date: date, area_acres, today: Optional[date] = None) -> list[dict[str, Any]]:
    """Build a stable machinery plan; today is injectable for deterministic tests."""
    current_date = today or datetime.now(IST).date()
    area = Decimal(str(area_acres))
    items = []
    for mapping in mappings:
        start = sowing_date + timedelta(days=mapping.stage.start_day + mapping.days_offset)
        end = start + timedelta(days=mapping.window_days)
        if end < current_date:
            status = "passed"
        elif start <= current_date <= end:
            status = "in_window"
        elif start <= current_date + timedelta(days=7):
            status = "due_soon"
        else:
            status = "upcoming"
        cost = calculate_group_costs([area], mapping.machine_type.typical_rate_per_acre, mapping.machine_type.mobilization_cost)
        solo_paise = cost["members"][0].solo_paise
        group_of_five = calculate_group_costs([area] * 5, mapping.machine_type.typical_rate_per_acre, mapping.machine_type.mobilization_cost)
        group_paise = group_of_five["members"][0].share_paise
        items.append({
            "machine_type_id": mapping.machine_type_id,
            "machine_type": {"name": mapping.machine_type.name, "name_hi": mapping.machine_type.name_hi, "name_mr": mapping.machine_type.name_mr},
            "stage": mapping.stage.stage_name,
            "needed_between": [start, end],
            "days_until": (start - current_date).days,
            "status": status,
            "estimated_cost_solo": {"paise": solo_paise, "rupees": solo_paise / 100},
            "estimated_cost_if_group_of_5": {"paise": group_paise, "rupees": group_paise / 100, "label": "Estimate"},
            "estimated_saving": {"paise": solo_paise - group_paise, "rupees": (solo_paise - group_paise) / 100, "label": "Estimate"},
            "source": mapping.source or SOURCE,
        })
    return sorted(items, key=lambda item: item["needed_between"][0])
