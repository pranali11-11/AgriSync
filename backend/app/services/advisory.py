"""Deterministic crop stage, soil rating, and nutrient advisory services."""
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

SOURCE = "SAMPLE - verify with ICAR / state agriculture dept"
THRESHOLDS_PATH = Path(__file__).parents[1] / "data" / "soil_thresholds.json"
with THRESHOLDS_PATH.open(encoding="utf-8") as thresholds_file:
    SOIL_THRESHOLDS = json.load(thresholds_file)

NUTRIENT_FIELDS = {
    "ph": "ph",
    "nitrogen": "nitrogen",
    "phosphorus": "phosphorus",
    "potassium": "potassium",
    "organic carbon": "organic_carbon",
    "organic_carbon": "organic_carbon",
}


@dataclass(frozen=True)
class StageResult:
    current: Optional[Any]
    next_stage: Optional[Any]
    days_until_next: Optional[int]
    timeline: list[dict[str, Any]]


def calculate_stage(days_since_sowing: int, stages: Iterable[Any]) -> StageResult:
    """Calculate a stage using inclusive start/end day boundaries."""
    ordered = sorted(stages, key=lambda stage: stage.start_day)
    timeline = [
        {"stage": stage.stage_name, "start_day": stage.start_day, "end_day": stage.end_day}
        for stage in ordered
    ]
    if not ordered:
        return StageResult(None, None, None, timeline)

    current_index = next(
        (index for index, stage in enumerate(ordered)
         if stage.start_day <= days_since_sowing <= stage.end_day),
        None,
    )
    if current_index is None:
        current_index = 0 if days_since_sowing < ordered[0].start_day else len(ordered) - 1

    next_stage = ordered[current_index + 1] if current_index + 1 < len(ordered) else None
    days_until_next = max(0, next_stage.start_day - days_since_sowing) if next_stage else None
    return StageResult(ordered[current_index], next_stage, days_until_next, timeline)


def days_since_sowing(sowing_date: date, today: Optional[date] = None) -> int:
    return max(0, ((today or date.today()) - sowing_date).days)


def rate_soil(soil_test: Any | Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Return deterministic low/adequate/high ratings for supplied measurements."""
    if soil_test is None:
        return {}
    values = soil_test if isinstance(soil_test, Mapping) else vars(soil_test)
    ratings = {}
    for nutrient, field in NUTRIENT_FIELDS.items():
        if nutrient != field and nutrient in ratings:
            continue
        value = values.get(field)
        if value is None:
            continue
        ranges = SOIL_THRESHOLDS[field]
        level = "high"
        for candidate in ("low", "adequate", "high"):
            bounds = ranges[candidate]
            lower_ok = bounds["min"] is None or value >= bounds["min"]
            upper_ok = bounds["max"] is None or value < bounds["max"]
            if lower_ok and upper_ok:
                level = candidate
                break
        ratings[field] = {"value": value, "level": level, "unit": ranges["unit"], "source": SOURCE}
    return ratings


def _condition_matches(
    condition: Mapping[str, Any],
    stage_name: str,
    ratings: Mapping[str, Any],
    irrigation_type: Optional[str] = None,
) -> bool:
    expected_stage = condition.get("stage")
    if expected_stage and expected_stage.casefold() != stage_name.casefold():
        return False
    cond_irr = condition.get("irrigation_type") or condition.get("irrigation")
    if cond_irr:
        if isinstance(cond_irr, list):
            if not irrigation_type or irrigation_type.casefold() not in [i.casefold() for i in cond_irr]:
                return False
        elif not irrigation_type or cond_irr.casefold() != irrigation_type.casefold():
            return False
    nutrient = condition.get("nutrient")
    levels = condition.get("level", [])
    if nutrient and levels:
        rating = ratings.get(NUTRIENT_FIELDS.get(nutrient.casefold(), nutrient.casefold()))
        return bool(rating and rating["level"] in levels)
    return True


def _recent_category(category: str, fertilizer_history: Iterable[Any], today: date, window_days: int) -> Optional[Any]:
    for record in fertilizer_history:
        if record.product_category.casefold() == category.casefold():
            age = (today - record.applied_on).days
            if 0 <= age <= window_days:
                return record
    return None


def match_rules(
    rules: Iterable[Any],
    current_stage: Any,
    next_stage: Optional[Any],
    ratings: Mapping[str, Any],
    fertilizer_history: Iterable[Any] = (),
    today: Optional[date] = None,
    recent_window_days: int = 21,
    days_since_sowing_value: Optional[int] = None,
    irrigation_type: Optional[str] = None,
    irrigation_type_note: Optional[str] = None,
) -> list[dict[str, Any]]:
    today = today or date.today()
    results = []
    is_drip = bool(irrigation_type and "drip" in irrigation_type.casefold())
    for rule in sorted(rules, key=lambda item: item.id):
        condition = rule.condition_json or {}
        status = "suggested"
        matched_stage = current_stage
        if not _condition_matches(condition, current_stage.stage_name, ratings, irrigation_type=irrigation_type):
            days_to_next = next_stage.start_day - days_since_sowing_value if next_stage and days_since_sowing_value is not None else 8
            if not next_stage or days_to_next > 7:
                continue
            if not _condition_matches(condition, next_stage.stage_name, ratings, irrigation_type=irrigation_type):
                continue
            status = "coming_up"
            matched_stage = next_stage
        recent = _recent_category(rule.input_category, fertilizer_history, today, recent_window_days)
        if recent:
            status = "recently_applied"
        guidance = rule.guidance_text
        if is_drip and "fertigation" not in guidance.lower() and rule.input_category.casefold() in ("fertilizer", "crop care"):
            guidance = f"{guidance} (Drip-fertigation note: Split application into weekly fertigation doses via venturi/tank for maximum efficiency.)"
        results.append({
            "rule_id": rule.id,
            "nutrient": rule.nutrient,
            "level": condition.get("level", ["general"])[0],
            "input_category": rule.input_category,
            "guidance_text": guidance,
            "source": rule.source or SOURCE,
            "stage": matched_stage.stage_name,
            "status": status,
            "applied_on": recent.applied_on.isoformat() if recent else None,
            "irrigation_type": irrigation_type,
        })
    return results


class ExplainerProvider(ABC):
    @abstractmethod
    async def explain(self, recommendations: list[dict[str, Any]], language: str) -> list[dict[str, Any]]:
        raise NotImplementedError


class NoopExplainer(ExplainerProvider):
    async def explain(self, recommendations: list[dict[str, Any]], language: str) -> list[dict[str, Any]]:
        return recommendations


class LLMExplainer(ExplainerProvider):
    def __init__(self, client: Any):
        self.client = client

    async def explain(self, recommendations: list[dict[str, Any]], language: str) -> list[dict[str, Any]]:
        original = json.dumps(recommendations, ensure_ascii=False)
        rewritten = await self.client.rewrite(original, language)
        if not _llm_output_is_safe(rewritten, original):
            return recommendations
        return [{**item, "guidance_text": rewritten} for item in recommendations]


def _llm_output_is_safe(output: str, rule_output: str) -> bool:
    if set(re.findall(r"\d+(?:\.\d+)?", output)) - set(re.findall(r"\d+(?:\.\d+)?", rule_output)):
        return False
    known_inputs = {"urea", "dap", "ssp", "mop", "compost", "farmyard manure", "zinc sulphate"}
    original_lower = rule_output.casefold()
    return not any(name in output.casefold() and name not in original_lower for name in known_inputs)
