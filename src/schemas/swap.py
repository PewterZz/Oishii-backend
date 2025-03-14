from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class SwapStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"

class SwapBase(BaseModel):
    requester_food_id: int
    provider_food_id: int
    message: Optional[str] = Field(None, max_length=500)

class SwapCreate(SwapBase):
    pass

class SwapUpdate(BaseModel):
    status: SwapStatus
    response_message: Optional[str] = Field(None, max_length=500)

class SwapResponse(SwapBase):
    id: int
    requester_id: int
    provider_id: int
    status: SwapStatus = SwapStatus.PENDING
    created_at: datetime
    updated_at: datetime
    response_message: Optional[str] = None

class SwapDetailResponse(SwapResponse):
    requester_food: dict
    provider_food: dict 