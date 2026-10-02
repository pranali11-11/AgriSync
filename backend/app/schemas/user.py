from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    name: str = Field(..., max_length=100)
    phone: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    role: str = Field(default="farmer", pattern="^(farmer|provider|admin)$")
    language: str = Field(default="en", pattern="^(en|hi|mr)$")


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FarmerProfileBase(BaseModel):
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    total_area_acres: float = Field(default=0.0, ge=0)


class FarmerProfileCreate(FarmerProfileBase):
    user_id: int


class FarmerProfileResponse(FarmerProfileBase):
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class ProviderBase(BaseModel):
    org_type: str = Field(default="owner", pattern="^(owner|FPO|CHC|service)$")
    verified: bool = False


class ProviderCreate(ProviderBase):
    user_id: int


class ProviderResponse(ProviderBase):
    user_id: int

    model_config = ConfigDict(from_attributes=True)
