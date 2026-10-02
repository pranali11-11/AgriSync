from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class MachineTypeBase(BaseModel):
    name: str
    name_hi: Optional[str] = None
    name_mr: Optional[str] = None
    typical_rate_per_acre: float
    mobilization_cost: float = 0.0


class MachineTypeCreate(MachineTypeBase):
    pass


class MachineTypeResponse(MachineTypeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class MachineBase(BaseModel):
    provider_id: int
    machine_type_id: int
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    rate_per_acre: float = Field(..., gt=0)
    available_from: date
    available_to: date
    verified: bool = False
    rating: float = Field(default=4.5, ge=0, le=5)


class MachineCreate(MachineBase):
    pass


class MachineResponse(MachineBase):
    id: int
    distance_km: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class CropMachineMapBase(BaseModel):
    crop_id: int
    stage_id: Optional[int] = None
    machine_type_id: int
    days_offset: int = 0


class CropMachineMapCreate(CropMachineMapBase):
    pass


class CropMachineMapResponse(CropMachineMapBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
