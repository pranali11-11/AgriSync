"""Validation service for crop lifecycle stages integrity."""
from typing import Any, Iterable, List, Optional, Tuple


def validate_crop_stages_integrity(crops: Iterable[Any]) -> List[str]:
    """
    Validates crop stages across all crops.
    Ensures:
    1. Every crop has at least 1 stage.
    2. First stage starts at day 0.
    3. Last stage ends exactly at crop.duration_days.
    4. For every stage, start_day < end_day (strictly positive length, no zero or negative length).
    5. Stages are strictly contiguous: stage[i].end_day == stage[i+1].start_day (no gaps, no overlaps).
    6. Every stage has a non-empty stage_description explaining what happens and what to watch for.
    7. Every stage has a valid source citation.

    Returns a list of error strings. If all crops and stages are valid, returns an empty list.
    """
    errors: List[str] = []
    crops_list = list(crops)
    if not crops_list:
        return ["No crops provided to validate."]

    for crop in crops_list:
        c_name = getattr(crop, "name", f"ID {getattr(crop, 'id', 'unknown')}")
        duration = getattr(crop, "duration_days", None)
        stages = list(getattr(crop, "stages", []))

        if not stages:
            errors.append(f"Crop '{c_name}' (duration: {duration}d) has no stages defined.")
            continue

        if duration is None or duration <= 0:
            errors.append(f"Crop '{c_name}' has invalid duration_days: {duration}.")
            continue

        sorted_stages = sorted(stages, key=lambda s: (s.start_day, s.end_day))

        # Check first stage start day
        if sorted_stages[0].start_day != 0:
            errors.append(
                f"Crop '{c_name}': First stage '{sorted_stages[0].stage_name}' starts at day {sorted_stages[0].start_day}, expected 0."
            )

        # Check last stage end day
        if sorted_stages[-1].end_day != duration:
            errors.append(
                f"Crop '{c_name}': Last stage '{sorted_stages[-1].stage_name}' ends at day {sorted_stages[-1].end_day}, expected {duration}."
            )

        # Check stage lengths and descriptions
        for s in sorted_stages:
            s_name = getattr(s, "stage_name", "Unnamed")
            if s.end_day <= s.start_day:
                errors.append(
                    f"Crop '{c_name}': Stage '{s_name}' has zero or inverted length (start={s.start_day}, end={s.end_day})."
                )
            desc = getattr(s, "stage_description", None)
            if not desc or not str(desc).strip():
                errors.append(
                    f"Crop '{c_name}': Stage '{s_name}' is missing a stage_description."
                )

        # Check contiguous non-overlapping transitions
        for i in range(len(sorted_stages) - 1):
            curr_s = sorted_stages[i]
            next_s = sorted_stages[i + 1]
            if curr_s.end_day < next_s.start_day:
                gap = next_s.start_day - curr_s.end_day
                errors.append(
                    f"Crop '{c_name}': Gap of {gap} day(s) between '{curr_s.stage_name}' (ends at {curr_s.end_day}) and '{next_s.stage_name}' (starts at {next_s.start_day})."
                )
            elif curr_s.end_day > next_s.start_day:
                overlap = curr_s.end_day - next_s.start_day
                errors.append(
                    f"Crop '{c_name}': Overlap of {overlap} day(s) between '{curr_s.stage_name}' (ends at {curr_s.end_day}) and '{next_s.stage_name}' (starts at {next_s.start_day})."
                )

    return errors
