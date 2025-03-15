from pydantic import BaseModel, EmailStr, Field, HttpUrl, UUID4
from typing import Optional, List
from datetime import datetime
from enum import Enum

class CookType(str, Enum):
    MEAL_PREPPER = "the meal prepper"
    DAILY_FRESH = "the daily fresh cook"
    ONE_BIG_BATCH = "the one-big-batch cook"
    NON_COOK = "the non-cook"

class CookFrequency(str, Enum):
    ONE_TO_TWO = "1-2 times"
    THREE_TO_FOUR = "3-4 times"
    FIVE_TO_SEVEN = "5-7 times"
    MORE_THAN_SEVEN = "more than 7 times"

class DietaryRequirement(str, Enum):
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    HALAL = "halal"
    NONE = "none"

class Purpose(str, Enum):
    SAVE_EXPENSES = "save on food expenses"
    EAT_HEALTHIER = "eat healthier meals"
    TRY_NEW_DISHES = "try out new dishes"
    MAKE_FRIENDS = "make new friends"

class Location(BaseModel):
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    formatted_address: str = Field(..., description="Human-readable address")

class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    bio: str = Field(..., min_length=10, max_length=500)
    cook_type: CookType
    cook_frequency: CookFrequency
    dietary_requirements: List[DietaryRequirement] = []
    allergies: str = Field(..., max_length=200)
    purpose: Purpose
    home_address: str = Field(..., min_length=5, max_length=200)
    location: Optional[Location] = None
    is_verified: bool = False

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    cook_type: Optional[str] = None
    cook_frequency: Optional[str] = None
    dietary_requirements: Optional[List[str]] = None
    allergies: Optional[str] = None
    purpose: Optional[str] = None
    home_address: Optional[str] = None
    location: Optional[Location] = None

class UserResponse(BaseModel):
    id: UUID4
    email: EmailStr
    first_name: str
    last_name: str
    bio: str
    cook_type: CookType
    cook_frequency: CookFrequency
    dietary_requirements: List[DietaryRequirement]
    allergies: str
    purpose: Purpose
    home_address: str
    location: Optional[Location] = None
    profile_picture: Optional[HttpUrl] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    swap_rating: Optional[float] = None
    is_verified: bool

class VerificationRequest(BaseModel):
    email: EmailStr
    code: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[str] = None 