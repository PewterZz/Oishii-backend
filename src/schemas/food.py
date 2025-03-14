from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum
from .user import DietaryRequirement

class FoodCategory(str, Enum):
    MEAL = "meal"
    SNACK = "snack"
    DESSERT = "dessert"
    DRINK = "drink"
    LEFTOVER = "leftover"

class FoodBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    category: FoodCategory
    dietary_requirements: List[DietaryRequirement] = []
    allergens: str = Field(..., max_length=200)
    expiry_date: Optional[datetime] = None
    location: str = Field(..., min_length=3, max_length=100)
    is_homemade: bool = False
    is_available: bool = True

class FoodCreate(FoodBase):
    image_url: Optional[str] = None
    
    @validator('expiry_date')
    def validate_expiry_date(cls, v):
        if v and v < datetime.now():
            raise ValueError("Expiry date cannot be in the past")
        return v

class FoodUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, min_length=10, max_length=500)
    category: Optional[FoodCategory] = None
    dietary_requirements: Optional[List[DietaryRequirement]] = None
    allergens: Optional[str] = Field(None, max_length=200)
    expiry_date: Optional[datetime] = None
    location: Optional[str] = Field(None, min_length=3, max_length=100)
    is_homemade: Optional[bool] = None
    is_available: Optional[bool] = None
    image_url: Optional[str] = None
    
    @validator('expiry_date')
    def validate_expiry_date(cls, v):
        if v and v < datetime.now():
            raise ValueError("Expiry date cannot be in the past")
        return v

class FoodResponse(FoodBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    image_url: Optional[str] = None 