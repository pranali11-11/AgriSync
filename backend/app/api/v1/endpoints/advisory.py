from datetime import date
import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_redis, require_role, RedisWrapper
from app.core.database import get_db
from app.core.config import settings
from app.models.crop import Crop
from app.models.farm import Farm, SoilTest
from app.models.user import User
from app.services.advisory import (
    NoopExplainer,
    calculate_stage,
    days_since_sowing,
    match_rules,
    rate_soil,
)

router = APIRouter()


class AssistantRequest(BaseModel):
    question: Optional[str] = Field(default=None, max_length=1000)


def _assistant_fallback(
    farm: Farm,
    stage_result: Any,
    ratings: dict[str, Any],
    recommendations: list[dict[str, Any]],
    question: Optional[str] = None,
) -> dict[str, Any]:
    steps = [
        {
            "task": item["guidance_text"],
            "timing": item["status"].replace("_", " ").title(),
            "reason": f"{item['nutrient'].replace('_', ' ').title()} status: {item['level']}",
            "quantity": "Follow the product label or local officer advice",
        }
        for item in recommendations
    ]
    if not steps:
        steps = [{
            "task": "Inspect the crop and confirm irrigation needs",
            "timing": "Today",
            "reason": "No stage-specific rule is available for this crop stage",
            "quantity": "Walk the field and record any stress or pest signs",
        }]
    warnings = []
    if farm.irrigation_type == "drip":
        steps.append({
            "task": "Schedule drip fertigation application",
            "timing": "This week",
            "reason": "Drip irrigation enables precise root-zone fertigation for maximum nutrient use efficiency",
            "quantity": "Inject water-soluble fertilizers in recommended stage splits and flush lines after application",
        })
    for nutrient, rating in ratings.items():
        if rating["level"] == "low":
            warnings.append(f"Low {nutrient.replace('_', ' ')} may affect crop growth.")
    if not ratings:
        warnings.append("Add a soil test for more precise nutrient guidance.")
    if question:
        steps.insert(0, {
            "task": f"For your question, review field conditions before acting: {question}",
            "timing": "Today",
            "reason": "The assistant is using the current crop stage and available farm data",
            "quantity": "Use measured field conditions and local agronomy guidance",
        })
    next_stage = stage_result.next_stage
    return {
        "currentStageAdvice": f"{farm.crop.name} is in {stage_result.current.stage_name}. Follow the steps below and monitor the field today.",
        "steps": steps,
        "upcomingMilestones": ([{
            "stage": next_stage.stage_name,
            "daysAway": stage_result.days_until_next,
            "prep": f"Prepare for {next_stage.stage_name} activities and check the crop regularly.",
        }] if next_stage else []),
        "warnings": warnings,
        "source": "rule-engine-fallback",
    }


async def _claude_assistant(context: dict[str, Any]) -> Optional[dict[str, Any]]:
    if settings.LLM_PROVIDER.casefold() != "claude" or not settings.LLM_API_KEY:
        return None
    prompt = """You are AgriSync, a careful agricultural advisory assistant. Use the supplied farm context. Return ONLY valid JSON, with exactly these keys: currentStageAdvice (string), steps (array of objects with task, timing, reason, quantity strings), upcomingMilestones (array of objects with stage, daysAway number, prep string), warnings (array of strings). Do not include markdown fences or extra text. Do not invent measurements. Give practical, conservative guidance and recommend a local agronomist for high-risk decisions.\n\nFarm context:\n""" + json.dumps(context, ensure_ascii=False)
    headers = {"x-api-key": settings.LLM_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    payload = {"model": "claude-3-5-haiku-latest", "max_tokens": 1200, "temperature": 0.2, "system": "Return JSON only.", "messages": [{"role": "user", "content": prompt}]}
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            response.raise_for_status()
            content = response.json()["content"][0]["text"].strip()
            content = content.removeprefix("```json").removesuffix("```").strip()
            result = json.loads(content)
            if not isinstance(result.get("steps"), list) or not isinstance(result.get("warnings"), list):
                return None
            return {**result, "source": "claude"}
    except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None

GENERAL_GUIDANCE = {
    "wheat": "Monitor crown root initiation, tillering, and moisture. Follow local agronomy guidance and get a soil test for accurate advice.",
    "rice": "Maintain suitable water levels, watch for leaf blast, and follow local agronomy guidance. Get a soil test for accurate advice.",
    "cotton": "Monitor square formation, boll development, and pest pressure. Get a soil test for accurate advice.",
    "soybean": "Monitor nodulation, moisture stress, and pod development. Get a soil test for accurate advice.",
    "sugarcane": "Monitor tillering, trash mulching, and irrigation intervals. Get a soil test for accurate advice.",
    "maize": "Check whorl moisture, nitrogen needs, and scout for fall armyworm. Get a soil test for accurate advice.",
    "bajra": "Ensure well-drained soil, monitor tillering, and check for downy mildew. Get a soil test for accurate advice.",
    "jowar": "Monitor shoot fly during early stages and drought stress during booting. Get a soil test for accurate advice.",
    "groundnut": "Maintain loose, friable soil for peg penetration and monitor for leaf spot. Get a soil test for accurate advice.",
    "tur/arhar": "Monitor branching, scout for pod borers during flowering, and avoid waterlogging. Get a soil test for accurate advice.",
    "gram (chana)": "Monitor root health to prevent wilt, manage helicoverpa pod borer. Get a soil test for accurate advice.",
    "moong": "Inspect for sucking pests, yellow mosaic virus, and ensure light irrigations. Get a soil test for accurate advice.",
    "urad": "Watch for powdery mildew, maintain proper drainage, and scout for pod borers. Get a soil test for accurate advice.",
    "mustard": "Scout for aphids during flowering and pod development, avoid waterlogging. Get a soil test for accurate advice.",
    "onion": "Monitor thrips and purple blotch, regulate irrigation before harvest. Get a soil test for accurate advice.",
    "tomato": "Provide staking support, scout for fruit borer and early/late blight. Get a soil test for accurate advice.",
    "potato": "Perform earthing up, inspect for late blight, and regulate tuber bulking irrigation. Get a soil test for accurate advice.",
    "turmeric": "Ensure raised beds with excellent drainage, prevent rhizome rot with organic mulch. Get a soil test for accurate advice.",
    "chilli": "Monitor for thrips, mites, and leaf curl; maintain balanced fertigation. Get a soil test for accurate advice.",
    "ginger": "Ensure partial shade/mulching, avoid waterlogging, and protect against soft rot. Get a soil test for accurate advice.",
}


async def _load_farm(db: AsyncSession, farm_id: int) -> Farm:
    statement = (
        select(Farm)
        .where(Farm.id == farm_id)
        .options(
            selectinload(Farm.crop).selectinload(Crop.stages),
            selectinload(Farm.crop).selectinload(Crop.nutrient_rules),
            selectinload(Farm.soil_tests),
            selectinload(Farm.fertilizer_records),
            selectinload(Farm.farmer).selectinload(User.farmer_profile),
        )
    )
    farm = (await db.execute(statement)).scalar_one_or_none()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    return farm


@router.get("/farms/{farm_id}/advisory")
async def get_advisory(
    farm_id: int,
    lang: str = Query("en", pattern="^(en|hi|mr)$"),
    current_user: User = Depends(require_role("farmer")),
    db: AsyncSession = Depends(get_db),
    redis: RedisWrapper = Depends(get_redis),
) -> dict[str, Any]:
    farm = await _load_farm(db, farm_id)
    if farm.farmer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to access this farm")

    elapsed = days_since_sowing(farm.sowing_date)
    stage_result = calculate_stage(elapsed, farm.crop.stages)
    if not stage_result.current:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Crop has no stages")

    latest_soil = max(farm.soil_tests, key=lambda item: item.tested_on, default=None)
    ratings = rate_soil(latest_soil) if latest_soil else {}
    rules = [rule for rule in farm.crop.nutrient_rules if rule.stage_id is not None]
    recommendations = match_rules(
        rules,
        stage_result.current,
        stage_result.next_stage,
        ratings,
        farm.fertilizer_records,
        days_since_sowing_value=elapsed,
        irrigation_type=farm.irrigation_type,
        irrigation_type_note=farm.irrigation_type_note,
    )
    if not latest_soil:
        recommendations = [{
            "rule_id": None,
            "nutrient": "general",
            "level": "not_assessed",
            "input_category": "Crop care",
            "guidance_text": GENERAL_GUIDANCE.get(farm.crop.name.casefold(), "Follow local agronomy guidance. Get a soil test for accurate advice."),
            "source": "SAMPLE - verify with ICAR / state agriculture dept",
            "stage": stage_result.current.stage_name,
            "status": "suggested",
            "applied_on": None,
        }]

    cache_key = "advisory:explanation:" + ":".join([
        ",".join(str(item["rule_id"]) for item in recommendations if item["rule_id"] is not None) or "general",
        lang,
    ])
    cached = await redis.get(cache_key)
    if cached:
        recommendations = json.loads(cached) if isinstance(cached, str) else cached
    else:
        recommendations = await NoopExplainer().explain(recommendations, lang)
        await redis.setex(cache_key, 86400, json.dumps(recommendations, ensure_ascii=False))

    return {
        "stage": {
            "name": stage_result.current.stage_name,
            "start_day": stage_result.current.start_day,
            "end_day": stage_result.current.end_day,
            "description": getattr(stage_result.current, "stage_description", None),
            "source": getattr(stage_result.current, "source", "SAMPLE - verify with ICAR / state agriculture dept"),
        },
        "days_since_sowing": elapsed,
        "next_stage": {
            "name": stage_result.next_stage.stage_name,
            "start_day": stage_result.next_stage.start_day,
            "end_day": stage_result.next_stage.end_day,
            "description": getattr(stage_result.next_stage, "stage_description", None),
            "source": getattr(stage_result.next_stage, "source", "SAMPLE - verify with ICAR / state agriculture dept"),
            "days_until": stage_result.days_until_next,
        } if stage_result.next_stage else None,
        "timeline": stage_result.timeline,
        "soil_ratings": ratings,
        "recommendations": recommendations,
        "soil_test_missing": latest_soil is None,
        "irrigation_type": farm.irrigation_type,
        "irrigation_type_note": farm.irrigation_type_note,
        "disclaimer": "Guidance only. Confirm with your local agriculture officer.",
    }


@router.post("/farms/{farm_id}/advisory/assistant")
async def ask_advisory_assistant(
    farm_id: int,
    payload: AssistantRequest,
    current_user: User = Depends(require_role("farmer")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    farm = await _load_farm(db, farm_id)
    if farm.farmer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to access this farm")

    elapsed = days_since_sowing(farm.sowing_date)
    stage_result = calculate_stage(elapsed, farm.crop.stages)
    if not stage_result.current:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Crop has no stages")
    latest_soil = max(farm.soil_tests, key=lambda item: item.tested_on, default=None)
    ratings = rate_soil(latest_soil) if latest_soil else {}
    recommendations = match_rules(
        [rule for rule in farm.crop.nutrient_rules if rule.stage_id is not None],
        stage_result.current,
        stage_result.next_stage,
        ratings,
        farm.fertilizer_records,
        days_since_sowing_value=elapsed,
        irrigation_type=farm.irrigation_type,
        irrigation_type_note=farm.irrigation_type_note,
    )
    context = {
        "crop": farm.crop.name,
        "sowingDate": farm.sowing_date.isoformat(),
        "currentDay": elapsed,
        "currentStage": stage_result.current.stage_name,
        "irrigationType": farm.irrigation_type,
        "irrigationNote": farm.irrigation_type_note,
        "soil": {
            "ph": latest_soil.ph if latest_soil else None,
            "nitrogen": latest_soil.nitrogen if latest_soil else None,
            "phosphorus": latest_soil.phosphorus if latest_soil else None,
            "potassium": latest_soil.potassium if latest_soil else None,
            "organicCarbon": latest_soil.organic_carbon if latest_soil else None,
        },
        "location": {
            "village": farm.farmer.farmer_profile.village if farm.farmer.farmer_profile else None,
            "district": farm.farmer.farmer_profile.district if farm.farmer.farmer_profile else None,
            "state": farm.farmer.farmer_profile.state if farm.farmer.farmer_profile else None,
        },
        "season": "current growing season",
        "ruleRecommendations": recommendations,
        "question": payload.question,
    }
    result = await _claude_assistant(context)
    return result or _assistant_fallback(farm, stage_result, ratings, recommendations, payload.question)
