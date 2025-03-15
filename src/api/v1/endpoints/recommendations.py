from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from uuid import UUID
import logging

from ....schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    FoodPreference
)
from ....core.datastax import (
    get_food_recommendations,
    save_user_profile
)
from ...v1.endpoints.users import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["recommendations"])


@router.post("/search", response_model=RecommendationResponse)
async def search_food_recommendations(
    request: RecommendationRequest,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """
    Search for food recommendations based on a search term.
    
    If a user is authenticated, their preferences will be considered in the recommendations.
    """
    try:
        user_id = None
        if current_user:
            user_id = UUID(current_user["id"])
        
        # Get recommendations from DataStax
        recommendations = await get_food_recommendations(
            search_term=request.search_term,
            user_id=user_id,
            limit=request.limit
        )
        
        return recommendations
    except Exception as e:
        logger.error(f"Error getting food recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get food recommendations"
        )


@router.post("/preferences", status_code=status.HTTP_201_CREATED)
async def update_food_preferences(
    preferences: FoodPreference,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a user's food preferences for better recommendations.
    
    This endpoint requires authentication.
    """
    try:
        # Ensure the user can only update their own preferences
        if str(preferences.user_id) != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own preferences"
            )
        
        # Save preferences to DataStax
        await save_user_profile(
            user_id=preferences.user_id,
            taste_preferences=preferences.taste_preferences,
            dietary_restrictions=preferences.dietary_restrictions,
            allergies=preferences.allergies,
            cuisine_preferences=preferences.cuisine_preferences
        )
        
        return {"message": "Food preferences updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating food preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update food preferences"
        ) 