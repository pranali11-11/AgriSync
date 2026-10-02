from typing import List
from pydantic import BaseModel, ConfigDict, Field


class InputSellerBase(BaseModel):
    name: str = Field(..., max_length=150)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    verified: bool = False
    categories: List[str]


class InputSellerCreate(InputSellerBase):
    pass


class InputSellerResponse(InputSellerBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
