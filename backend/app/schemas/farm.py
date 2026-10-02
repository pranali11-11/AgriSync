from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SoilTestBase(BaseModel):
    ph: float = Field(..., ge=0, le=14)
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    organic_carbon: Optional[float] = None
    tested_on: date


class SoilTestCreate(SoilTestBase):
    farm_id: int


class SoilTestResponse(SoilTestBase):
    id: int
    farm_id: int

    model_config = ConfigDict(from_attributes=True)


class FertilizerHistoryBase(BaseModel):
    product_category: str
    applied_on: date
    quantity_kg: float = Field(..., gt=0)


class FertilizerHistoryCreate(FertilizerHistoryBase):
    farm_id: int


class FertilizerHistoryResponse(FertilizerHistoryBase):
    id: int
    farm_id: int

    model_config = ConfigDict(from_attributes=True)


from app.models.farm import IrrigationType


def validate_irrigation_input(irrigation_type: Optional[str], irrigation_type_note: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not irrigation_type:
        return None, irrigation_type_note

    try:
        canonical = IrrigationType(irrigation_type).value
    except ValueError:
        canonical = str(irrigation_type).strip().lower()

    if canonical == IrrigationType.other.value:
        if not irrigation_type_note or not str(irrigation_type_note).strip():
            raise ValueError("Free-text note is required when irrigation type is 'other'")
        return canonical, str(irrigation_type_note).strip()

    return canonical, irrigation_type_note


class FarmBase(BaseModel):
    farmer_id: int
    crop_id: int
    sowing_date: date
    area_acres: float = Field(..., gt=0)
    soil_type: Optional[str] = None
    current_stage: Optional[str] = None
    irrigation_type: Optional[str] = None
    irrigation_type_note: Optional[str] = None


class FarmCreate(FarmBase):
    @model_validator(mode="after")
    def validate_irrigation(self):
        norm_type, norm_note = validate_irrigation_input(self.irrigation_type, self.irrigation_type_note)
        self.irrigation_type = norm_type
        self.irrigation_type_note = norm_note
        return self


class FarmResponse(FarmBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
