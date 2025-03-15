from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum
from uuid import UUID
from .user import DietaryRequirement

class FoodCategory(str, Enum):
    MEAL = "meal"
    SNACK = "snack"
    DESSERT = "dessert"
    DRINK = "drink"
    LEFTOVER = "leftover"

class FoodType(str, Enum):
    OFFERING = "offering"  # A meal being offered by a student
    REQUEST = "request"    # A meal being requested by a student

class FoodBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    category: FoodCategory
    food_type: FoodType = FoodType.OFFERING
    dietary_requirements: List[DietaryRequirement] = []
    allergens: str = Field(..., max_length=200)
    expiry_date: Optional[datetime] = None
    location: str = Field(..., min_length=3, max_length=100)
    is_homemade: bool = False
    is_available: bool = True
    pickup_times: Optional[List[str]] = None
    tickets_required: int = Field(1, ge=0, description="Number of tickets required to claim this meal")

class FoodCreate(FoodBase):
    image_url: Optional[str] = None
    
    @validator('expiry_date')
    def validate_expiry_date(cls, v):
        if v and v < datetime.now(v.tzinfo):
            raise ValueError("Expiry date cannot be in the past")
        return v

class FoodUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, min_length=10, max_length=500)
    category: Optional[FoodCategory] = None
    food_type: Optional[FoodType] = None
    dietary_requirements: Optional[List[DietaryRequirement]] = None
    allergens: Optional[str] = Field(None, max_length=200)
    expiry_date: Optional[datetime] = None
    location: Optional[str] = Field(None, min_length=3, max_length=100)
    is_homemade: Optional[bool] = None
    is_available: Optional[bool] = None
    image_url: Optional[str] = None
    pickup_times: Optional[List[str]] = None
    tickets_required: Optional[int] = Field(None, ge=0)
    
    @validator('expiry_date')
    def validate_expiry_date(cls, v):
        if v and v < datetime.now(v.tzinfo):
            raise ValueError("Expiry date cannot be in the past")
        return v

class FoodResponse(FoodBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    image_url: Optional[str] = None 