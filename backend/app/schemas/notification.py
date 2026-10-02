from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class NotificationBase(BaseModel):
    user_id: int
    type: str = Field(..., pattern="^(advisory|booking|alert|system)$")
    message: str
    channel: str = Field(default="in_app", pattern="^(in_app|sms|whatsapp)$")
    read: bool = False


class NotificationCreate(NotificationBase):
    pass


class NotificationResponse(NotificationBase):
    id: int
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)
