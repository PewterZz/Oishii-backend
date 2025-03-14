from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class RatingBase(BaseModel):
    swap_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=500)

class RatingCreate(RatingBase):
    pass

class RatingResponse(RatingBase):
    id: int
    rater_id: int
    rated_user_id: int
    created_at: datetime 