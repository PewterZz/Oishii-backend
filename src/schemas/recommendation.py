from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
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


# New schemas for AI-powered recommendations

class AIRecommendationRequest(BaseModel):
    """Request for AI-powered food recommendations"""
    query: str
    include_user_preferences: bool = True
    limit: int = 5
    tweaks: Optional[Dict[str, Any]] = None


class AIFoodRecommendation(BaseModel):
    """AI-generated food recommendation"""
    name: str
    description: Optional[str] = None
    ingredients: Optional[List[str]] = None
    preparation: Optional[str] = None
    nutritional_info: Optional[Dict[str, Any]] = None
    cuisine_type: Optional[str] = None
    dietary_tags: Optional[List[str]] = None
    confidence_score: Optional[float] = None
    food_id: Optional[str] = None  # ID of the food in the database if it exists
    database_item: Optional[Dict[str, Any]] = None  # Full details of the food from the database


class AIRecommendationResponse(BaseModel):
    """Response containing AI-powered food recommendations"""
    success: bool
    query: str
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    user_preferences_applied: bool = False
    error: Optional[str] = None
    raw_result: Optional[str] = None  # Raw result from the AI for debugging


# Schemas for Dr. Foodlove recommendations

class DrFoodloveRequest(BaseModel):
    """Request for Dr. Foodlove food recommendations"""
    query: str
    include_user_preferences: bool = True
    limit: int = 5
    detailed_response: bool = False
    custom_preferences: Optional[Dict[str, Any]] = None
    item_id: Optional[str] = None


class DrFoodloveNutritionInfo(BaseModel):
    """Nutritional information for a food recommendation"""
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    vitamins: Optional[List[str]] = None
    minerals: Optional[List[str]] = None


class DrFoodloveRecommendation(BaseModel):
    """Dr. Foodlove food recommendation"""
    name: str
    description: Optional[str] = None
    ingredients: Optional[List[str]] = None
    preparation: Optional[str] = None
    nutritional_info: Optional[Dict[str, Any]] = None
    cuisine_type: Optional[str] = None
    dietary_tags: Optional[List[str]] = None
    health_benefits: Optional[List[str]] = None
    meal_type: Optional[str] = None
    difficulty: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    total_time: Optional[str] = None
    servings: Optional[int] = None
    food_id: Optional[str] = None  # ID of the food in the database if it exists
    database_item: Optional[Dict[str, Any]] = None  # Full details of the food from the database
    image_url: Optional[str] = None  # URL to an image of the food


class DrFoodloveHealthInsights(BaseModel):
    """Health insights from Dr. Foodlove"""
    variety: int
    nutrient_focus: List[str] = Field(default_factory=list)
    balance_score: int
    recommendations: List[str] = Field(default_factory=list)


class DrFoodloveResponse(BaseModel):
    """Response containing Dr. Foodlove food recommendations"""
    success: bool
    query: str
    provider: str = "Dr. Foodlove AI"
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    user_preferences_applied: bool = False
    health_insights: Optional[DrFoodloveHealthInsights] = None
    error: Optional[str] = None
    conversation: Optional[str] = None
    food_item: Optional[Dict[str, Any]] = None
    raw_result: Optional[str] = None  # Raw result from the AI for debugging 