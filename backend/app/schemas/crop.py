from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class CropStageBase(BaseModel):
    stage_name: str
    start_day: int = Field(..., ge=0)
    end_day: int = Field(..., ge=0)
    stage_description: Optional[str] = None
    source: str = "SAMPLE - verify with ICAR / state agriculture dept"


class CropStageCreate(CropStageBase):
    crop_id: int


class CropStageResponse(CropStageBase):
    id: int
    crop_id: int

    model_config = ConfigDict(from_attributes=True)


class CropBase(BaseModel):
    name: str = Field(..., max_length=100)
    name_hi: Optional[str] = None
    name_mr: Optional[str] = None
    duration_days: int = Field(..., gt=0)
    category: str = Field(default="other", max_length=50)


class CropCreate(CropBase):
    pass


class CropResponse(CropBase):
    id: int
    stages: List[CropStageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class NutrientRuleBase(BaseModel):
    crop_id: int
    stage_id: Optional[int] = None
    nutrient: str
    condition_json: Dict[str, Any]
    guidance_text: str
    input_category: str
    source: str = "SAMPLE - verify with ICAR / state agriculture dept"


class NutrientRuleCreate(NutrientRuleBase):
    pass


class NutrientRuleResponse(NutrientRuleBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
