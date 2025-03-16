from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from typing import Optional, Dict, Any, List
from uuid import UUID
import logging
import json
import tempfile
import os
from pydantic import BaseModel

from ....schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    FoodPreference,
    AIRecommendationRequest,
    AIRecommendationResponse,
    DrFoodloveRequest,
    DrFoodloveResponse
)
from ....core.datastax import (
    get_food_recommendations,
    save_user_profile
)
from ....services.langflow_service import get_ai_food_recommendations
from ....services.dr_foodlove_service import get_dr_foodlove_recommendations
from ...v1.endpoints.users import get_current_user
from ....core.supabase import execute_query

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


@router.post("/ai-recommendations", response_model=AIRecommendationResponse)
async def get_ai_recommendations(
    request: AIRecommendationRequest,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """
    Get AI-powered food recommendations using DataStax Langflow.
    
    This endpoint can use the authenticated user's preferences to enhance recommendations.
    """
    try:
        # Get user preferences if requested and user is authenticated
        user_preferences: Optional[Dict[str, Any]] = None
        
        if request.include_user_preferences and current_user:
            # Get user preferences from database
            user_id = UUID(current_user["id"])
            
            # Construct user preferences dictionary
            # This would typically come from your database
            # For now, we'll use a simplified version based on the current user data
            user_preferences = {
                "user_id": str(user_id),
                "name": current_user.get("full_name", ""),
                "email": current_user.get("email", ""),
                # Add any other preferences from your user profile
                "dietary_restrictions": current_user.get("dietary_restrictions", []),
                "allergies": current_user.get("allergies", []),
                "cuisine_preferences": current_user.get("cuisine_preferences", [])
            }
        
        # Fetch available foods from the database to provide context to the AI
        available_foods = []
        try:
            # Get a sample of available foods from the database
            foods_result = await execute_query(
                table="foods",
                query_type="select",
                filters={"is_available": True},
                limit=50  # Limit to 50 foods to avoid token limits
            )
            
            if foods_result and len(foods_result) > 0:
                # Extract relevant information from each food
                available_foods = [
                    {
                        "name": food.get("title", ""),
                        "description": food.get("description", ""),
                        "category": food.get("category", ""),
                        "dietary_requirements": food.get("dietary_requirements", []),
                        "allergens": food.get("allergens", []),
                        "id": str(food.get("id", ""))
                    }
                    for food in foods_result
                ]
                
                logger.info(f"Fetched {len(available_foods)} available foods for AI context")
            else:
                logger.warning("No available foods found in the database")
        except Exception as e:
            logger.error(f"Error fetching available foods: {e}")
            # Continue without available foods if there's an error
        
        # Get AI recommendations
        ai_recommendations = await get_ai_food_recommendations(
            query=request.query,
            user_preferences=user_preferences,
            limit=request.limit,
            available_foods=available_foods
        )
        
        # If recommendations include food IDs from our database, fetch the full details
        if ai_recommendations.get("success") and ai_recommendations.get("recommendations"):
            for recommendation in ai_recommendations["recommendations"]:
                # Check if the recommendation has a food_id field that matches our database
                if "food_id" in recommendation and recommendation["food_id"]:
                    try:
                        food_id = recommendation["food_id"]
                        food_details = await execute_query(
                            table="foods",
                            query_type="select",
                            filters={"id": food_id}
                        )
                        
                        if food_details and len(food_details) > 0:
                            recommendation["database_item"] = food_details[0]
                    except Exception as e:
                        logger.error(f"Error fetching food details for ID {recommendation.get('food_id')}: {e}")
        
        return ai_recommendations
    except Exception as e:
        logger.error(f"Error getting AI food recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get AI food recommendations: {str(e)}"
        )


@router.post("/dr-foodlove", response_model=DrFoodloveResponse)
async def dr_foodlove_recommendations(
    request: DrFoodloveRequest,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """
    Get personalized food recommendations from Dr. Foodlove AI.
    
    This endpoint provides nutritionally balanced recommendations based on user preferences.
    If an item_id is provided, it will fetch the details of that food item.
    """
    try:
        # Check if item_id is provided and fetch food item details
        food_item = None
        if request.item_id:
            try:
                food_id = UUID(request.item_id)
                
                # Fetch food item from database
                food_items = await execute_query(
                    table="foods",
                    query_type="select",
                    filters={"id": str(food_id)}
                )
                
                if food_items and len(food_items) > 0:
                    food_item = food_items[0]
                    # Add the food item to the request query for context
                    request.query = f"Tell me about this food: {food_item['title']}. {request.query}"
            except Exception as e:
                logger.error(f"Error fetching food item: {e}")
                # Continue with the request even if food item fetch fails
        
        # Get user preferences if requested and user is authenticated
        user_preferences: Optional[Dict[str, Any]] = None
        
        if request.include_user_preferences and current_user:
            # Get user preferences from database
            user_id = UUID(current_user["id"])
            
            # Construct user preferences dictionary
            user_preferences = {
                "user_id": str(user_id),
                "name": current_user.get("full_name", ""),
                "email": current_user.get("email", ""),
                "dietary_restrictions": current_user.get("dietary_restrictions", []),
                "allergies": current_user.get("allergies", []),
                "cuisine_preferences": current_user.get("cuisine_preferences", []),
                "health_goals": current_user.get("health_goals", [])
            }
            
            # Add any custom preferences from the request
            if request.custom_preferences:
                user_preferences.update(request.custom_preferences)
        elif request.custom_preferences:
            # Use only custom preferences if provided
            user_preferences = request.custom_preferences
        
        # Fetch available foods from the database to provide context to the AI
        available_foods = []
        try:
            # Get a sample of available foods from the database
            foods_result = await execute_query(
                table="foods",
                query_type="select",
                filters={"is_available": True},
                limit=50  # Limit to 50 foods to avoid token limits
            )
            
            if foods_result and len(foods_result) > 0:
                # Extract relevant information from each food
                available_foods = [
                    {
                        "name": food.get("title", ""),
                        "description": food.get("description", ""),
                        "category": food.get("category", ""),
                        "dietary_requirements": food.get("dietary_requirements", []),
                        "allergens": food.get("allergens", []),
                        "id": str(food.get("id", ""))
                    }
                    for food in foods_result
                ]
                
                logger.info(f"Fetched {len(available_foods)} available foods for Dr. FoodLove context")
            else:
                logger.warning("No available foods found in the database")
        except Exception as e:
            logger.error(f"Error fetching available foods: {e}")
            # Continue without available foods if there's an error
        
        # Get Dr. Foodlove recommendations
        recommendations = await get_dr_foodlove_recommendations(
            query=request.query,
            user_preferences=user_preferences,
            limit=request.limit,
            detailed_response=request.detailed_response,
            available_foods=available_foods
        )
        
        # Add food item to the response if it was fetched
        if food_item:
            recommendations["food_item"] = food_item
            
        # If recommendations include food IDs from our database, fetch the full details
        if recommendations.get("success") and recommendations.get("recommendations"):
            for recommendation in recommendations["recommendations"]:
                # Check if the recommendation has a food_id field that matches our database
                if "food_id" in recommendation and recommendation["food_id"]:
                    try:
                        food_id = recommendation["food_id"]
                        food_details = await execute_query(
                            table="foods",
                            query_type="select",
                            filters={"id": food_id}
                        )
                        
                        if food_details and len(food_details) > 0:
                            recommendation["database_item"] = food_details[0]
                    except Exception as e:
                        logger.error(f"Error fetching food details for ID {recommendation.get('food_id')}: {e}")
        
        return recommendations
    except Exception as e:
        logger.error(f"Error getting Dr. Foodlove recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Dr. Foodlove recommendations: {str(e)}"
        )


@router.post("/dr-foodlove/image")
async def get_dr_foodlove_image_recommendations(
    query: str = Form(...),
    food_image: UploadFile = File(...),
    include_user_preferences: bool = Form(False),
    limit: int = Form(5),
    detailed_response: bool = Form(False),
    custom_preferences: Optional[str] = Form(None),
    current_user: Optional[dict] = Depends(get_current_user)
):
    """
    Get food recommendations from Dr. Foodlove AI based on an uploaded food image.
    
    This endpoint analyzes the uploaded image and provides nutritionally balanced recommendations.
    """
    try:
        # Save the uploaded image to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(food_image.filename)[1]) as temp_file:
            temp_file.write(await food_image.read())
            temp_file_path = temp_file.name
        
        # Parse custom preferences if provided
        parsed_custom_preferences = None
        if custom_preferences:
            try:
                parsed_custom_preferences = json.loads(custom_preferences)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON format for custom_preferences"
                )
        
        # Get user preferences if requested and user is authenticated
        user_preferences: Optional[Dict[str, Any]] = None
        
        if include_user_preferences and current_user:
            # Get user preferences from database
            user_id = UUID(current_user["id"])
            
            # Construct user preferences dictionary
            user_preferences = {
                "user_id": str(user_id),
                "name": current_user.get("full_name", ""),
                "email": current_user.get("email", ""),
                "dietary_restrictions": current_user.get("dietary_restrictions", []),
                "allergies": current_user.get("allergies", []),
                "cuisine_preferences": current_user.get("cuisine_preferences", []),
                "health_goals": current_user.get("health_goals", [])
            }
            
            # Add any custom preferences
            if parsed_custom_preferences:
                user_preferences.update(parsed_custom_preferences)
        elif parsed_custom_preferences:
            # Use only custom preferences if provided
            user_preferences = parsed_custom_preferences
        
        # Fetch available foods from the database to provide context to the AI
        available_foods = []
        try:
            # Get a sample of available foods from the database
            foods_result = await execute_query(
                table="foods",
                query_type="select",
                filters={"is_available": True},
                limit=50  # Limit to 50 foods to avoid token limits
            )
            
            if foods_result and len(foods_result) > 0:
                # Extract relevant information from each food
                available_foods = [
                    {
                        "name": food.get("title", ""),
                        "description": food.get("description", ""),
                        "category": food.get("category", ""),
                        "dietary_requirements": food.get("dietary_requirements", []),
                        "allergens": food.get("allergens", []),
                        "id": str(food.get("id", ""))
                    }
                    for food in foods_result
                ]
                
                logger.info(f"Fetched {len(available_foods)} available foods for Dr. FoodLove image context")
            else:
                logger.warning("No available foods found in the database")
        except Exception as e:
            logger.error(f"Error fetching available foods: {e}")
            # Continue without available foods if there's an error
        
        # Get Dr. Foodlove recommendations with the image
        recommendations = await get_dr_foodlove_recommendations(
            query=query,
            user_preferences=user_preferences,
            limit=limit,
            food_image_path=temp_file_path,
            detailed_response=detailed_response,
            available_foods=available_foods
        )
        
        # If recommendations include food IDs from our database, fetch the full details
        if recommendations.get("success") and recommendations.get("recommendations"):
            for recommendation in recommendations["recommendations"]:
                # Check if the recommendation has a food_id field that matches our database
                if "food_id" in recommendation and recommendation["food_id"]:
                    try:
                        food_id = recommendation["food_id"]
                        food_details = await execute_query(
                            table="foods",
                            query_type="select",
                            filters={"id": food_id}
                        )
                        
                        if food_details and len(food_details) > 0:
                            recommendation["database_item"] = food_details[0]
                    except Exception as e:
                        logger.error(f"Error fetching food details for ID {recommendation.get('food_id')}: {e}")
        
        # Clean up the temporary file
        os.unlink(temp_file_path)
        
        return recommendations
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Dr. Foodlove image recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Dr. Foodlove image recommendations: {str(e)}"
        ) 