"""Pure group cost calculations using integer paise."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable


@dataclass(frozen=True)
class MemberCost:
    member_index: int
    acres: Decimal
    share_paise: int
    solo_paise: int
    savings_paise: int


def _paise(value: Decimal | int | float | str) -> int:
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _largest_remainder(values: list[Decimal], total_paise: int) -> list[int]:
    floors = [int(value // 1) for value in values]
    remaining = total_paise - sum(floors)
    order = sorted(range(len(values)), key=lambda index: values[index] - floors[index], reverse=True)
    for index in order[:remaining]:
        floors[index] += 1
    return floors


def calculate_group_costs(acres: Iterable[Decimal | int | float | str], rate_per_acre: Decimal | int | float | str, mobilization_cost: Decimal | int | float | str) -> dict:
    """Return exact paise shares, solo costs, and savings for each member."""
    acre_values = [Decimal(str(value)) for value in acres]
    if not acre_values or any(value <= 0 for value in acre_values):
        raise ValueError("Every member must have positive acres")
    total_acres = sum(acre_values)
    rate_paise = _paise(rate_per_acre)
    mobilization_paise = _paise(mobilization_cost)
    machine_costs = [value * rate_paise for value in acre_values]
    mobilization_shares = [mobilization_paise * value / total_acres for value in acre_values]
    exact_shares = [machine + mobilization for machine, mobilization in zip(machine_costs, mobilization_shares)]
    group_total = int(sum(machine_costs) + mobilization_paise)
    shares = _largest_remainder(exact_shares, group_total)
    members = []
    for index, (member_acres, share) in enumerate(zip(acre_values, shares)):
        solo = _paise(member_acres * Decimal(str(rate_per_acre)) + Decimal(str(mobilization_cost)))
        members.append(MemberCost(index, member_acres, share, solo, solo - share))
    return {
        "total_paise": group_total,
        "total_acres": total_acres,
        "members": members,
    }


def preview_member_cost(acres, existing_acres, rate_per_acre, mobilization_cost) -> MemberCost:
    result = calculate_group_costs([*existing_acres, acres], rate_per_acre, mobilization_cost)
    return result["members"][-1]
