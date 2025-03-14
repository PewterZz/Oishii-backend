from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class NotificationType(str, Enum):
    SWAP_REQUEST = "swap_request"
    SWAP_ACCEPTED = "swap_accepted"
    SWAP_REJECTED = "swap_rejected"
    SWAP_COMPLETED = "swap_completed"
    FOOD_EXPIRING = "food_expiring"
    SYSTEM = "system"

class NotificationBase(BaseModel):
    user_id: int
    type: NotificationType
    title: str = Field(..., max_length=100)
    message: str = Field(..., max_length=500)
    related_id: Optional[int] = None  # ID of related entity (swap, food, etc.)

class NotificationCreate(NotificationBase):
    pass

class NotificationUpdate(BaseModel):
    is_read: bool = True

class NotificationResponse(NotificationBase):
    id: int
    created_at: datetime
    is_read: bool = False 