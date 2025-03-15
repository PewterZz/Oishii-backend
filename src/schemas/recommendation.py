from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class FoodPreference(BaseModel):
    """User's food preferences for recommendation matching"""
    user_id: UUID
    taste_preferences: List[str] = Field(default_factory=list)
    dietary_restrictions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    cuisine_preferences: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RecommendationRequest(BaseModel):
    """Request for food recommendations"""
    search_term: str
    user_id: Optional[UUID] = None
    limit: int = 10


class FoodRecommendation(BaseModel):
    """Food recommendation response"""
    food_id: UUID
    name: str
    description: Optional[str] = None
    cuisine_type: Optional[str] = None
    ingredients: List[str] = Field(default_factory=list)
    match_score: float = Field(ge=0.0, le=1.0)
    image_url: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Response containing food recommendations"""
    recommendations: List[FoodRecommendation] = Field(default_factory=list)
    total: int
    search_term: str 