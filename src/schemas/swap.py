from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from uuid import UUID

class SwapStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"

class SwapBase(BaseModel):
    provider_food_id: UUID
    requester_food_id: UUID
    message: Optional[str] = Field(None, max_length=500)

class SwapCreate(SwapBase):
    provider_id: UUID

class SwapUpdate(BaseModel):
    status: SwapStatus
    response_message: Optional[str] = Field(None, max_length=500)

class SwapResponse(BaseModel):
    id: UUID
    requester_id: UUID
    provider_id: UUID
    requester_food_id: UUID
    provider_food_id: UUID
    message: Optional[str] = None
    response_message: Optional[str] = None
    status: SwapStatus = SwapStatus.PENDING
    created_at: datetime
    updated_at: datetime

class SwapDetailResponse(SwapResponse):
    requester_food: dict
    provider_food: dict 