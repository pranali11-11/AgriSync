from datetime import date
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class GroupMemberBase(BaseModel):
    group_id: int
    farmer_id: int
    farm_id: int
    acres: float = Field(..., gt=0)
    share_amount: float = Field(..., ge=0)
    status: str = Field(default="joined", pattern="^(joined|paid|cancelled)$")


class GroupMemberCreate(GroupMemberBase):
    pass


class GroupMemberResponse(GroupMemberBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class BookingGroupBase(BaseModel):
    machine_id: int
    scheduled_date: date
    status: str = Field(default="open", pattern="^(open|confirmed|completed|cancelled)$")
    min_farmers: int = Field(default=2, gt=0)
    max_acres: float = Field(default=20.0, gt=0)
    created_by: int


class BookingGroupCreate(BookingGroupBase):
    pass


class BookingGroupResponse(BookingGroupBase):
    id: int
    members: List[GroupMemberResponse] = []

    model_config = ConfigDict(from_attributes=True)
