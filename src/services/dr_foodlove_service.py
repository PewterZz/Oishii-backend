import os
import json
import logging
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from .langflow_service import run_langflow, get_ai_food_recommendations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dr. Foodlove specific configuration
DR_FOODLOVE_PROMPT_TEMPLATE = """
You are Dr. Foodlove, an AI nutritionist and food expert. 
Based on the following information, provide personalized food recommendations:

Query: {query}

{preferences_section}

{available_foods_section}

IMPORTANT GUIDELINES:
1. ONLY recommend foods that are likely to exist in a typical food database.
2. DO NOT invent fictional dishes or make up random food items.
3. Provide recommendations in a structured format as shown below.
4. Focus on real, common dishes that match the user's query and preferences.
5. Include nutritional benefits where relevant.
6. If dietary restrictions are provided, strictly adhere to them.
7. If available foods are provided, prioritize recommending those foods.

Please provide {limit} food recommendations that are:
1. Nutritionally balanced
2. Aligned with the user's preferences and restrictions
3. Practical to prepare
4. Varied in cuisine types

YOUR RESPONSE MUST BE IN THIS JSON FORMAT:
```json
[
  {{
    "name": "Specific Dish Name",
    "description": "Brief description of the dish and why it matches the query",
    "ingredients": ["ingredient1", "ingredient2", "ingredient3"],
    "preparation": "Brief preparation method (optional)",
    "nutritional_info": "Brief nutritional highlights",
    "cuisine_type": "Cuisine category",
    "dietary_tags": ["tag1", "tag2"],
    "food_id": "ID of the food in the database (if available)"
  }},
  {{
    // Additional recommendations...
  }}
]
```

DO NOT include any text outside the JSON structure. Your entire response should be valid JSON that can be parsed programmatically.
"""


async def get_dr_foodlove_recommendations(
    query: str,
    user_preferences: Optional[Dict[str, Any]] = None,
    limit: int = 5,
    food_image_path: Optional[str] = None,
    detailed_response: bool = False,
    available_foods: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Get personalized food recommendations from Dr. Foodlove AI.
    
    Args:
        query: The user's food query or request
        user_preferences: Optional user preferences to customize recommendations
        limit: Maximum number of recommendations to return
        food_image_path: Optional path to a food image for analysis
        detailed_response: Whether to include detailed nutritional information
        available_foods: Optional list of available foods in the database to constrain recommendations
        
    Returns:
        Dictionary containing AI recommendations and metadata
    """
    # Log the input parameters for debugging
    logger.info(f"Dr.Foodlove API called with query: '{query}'")
    logger.info(f"User preferences provided: {user_preferences is not None}")
    logger.info(f"Available foods provided: {available_foods is not None}")
    logger.info(f"Limit: {limit}, Detailed response: {detailed_response}")
    
    # Format the preferences section if provided
    preferences_section = ""
    if user_preferences:
        preferences_str = []
        
        # Add dietary restrictions
        if user_preferences.get("dietary_restrictions"):
            restrictions = ", ".join(user_preferences.get("dietary_restrictions", []))
            preferences_str.append(f"Dietary Restrictions: {restrictions}")
        
        # Add allergies
        if user_preferences.get("allergies"):
            allergies = ", ".join(user_preferences.get("allergies", []))
            preferences_str.append(f"Allergies: {allergies}")
        
        # Add cuisine preferences
        if user_preferences.get("cuisine_preferences"):
            cuisines = ", ".join(user_preferences.get("cuisine_preferences", []))
            preferences_str.append(f"Preferred Cuisines: {cuisines}")
        
        # Add health goals
        if user_preferences.get("health_goals"):
            goals = ", ".join(user_preferences.get("health_goals", []))
            preferences_str.append(f"Health Goals: {goals}")
        
        # Add any other preferences
        for key, value in user_preferences.items():
            if key not in ["dietary_restrictions", "allergies", "cuisine_preferences", "health_goals", "user_id", "name", "email"]:
                if isinstance(value, list):
                    value_str = ", ".join(value)
                    preferences_str.append(f"{key.replace('_', ' ').title()}: {value_str}")
                elif isinstance(value, (str, int, float, bool)):
                    preferences_str.append(f"{key.replace('_', ' ').title()}: {value}")
        
        preferences_section = "User Preferences:\n" + "\n".join(preferences_str)
    else:
        preferences_section = "No specific user preferences provided."
    
    # Format the available foods section if provided
    available_foods_section = ""
    if available_foods and len(available_foods) > 0:
        # Limit the number of foods to include to avoid token limits
        food_sample = available_foods[:20] if len(available_foods) > 20 else available_foods
        
        # Format the available foods as a list
        foods_list = []
        for food in food_sample:
            food_info = f"{food.get('name', '')} (ID: {food.get('id', '')})"
            if food.get('category'):
                food_info += f" - Category: {food.get('category')}"
            if food.get('dietary_requirements') and len(food.get('dietary_requirements')) > 0:
                food_info += f" - Dietary: {', '.join(food.get('dietary_requirements'))}"
            foods_list.append(food_info)
        
        available_foods_section = "Available Foods in Database:\n" + "\n".join(foods_list)
        
        # Add a note to use food IDs when possible
        available_foods_section += "\n\nWhen recommending any of these foods, please include their ID in the food_id field."
    else:
        available_foods_section = "No specific available foods provided."
    
    # Format the prompt
    prompt = DR_FOODLOVE_PROMPT_TEMPLATE.format(
        query=query,
        preferences_section=preferences_section,
        available_foods_section=available_foods_section,
        limit=limit
    )
    
    # Log the formatted prompt
    logger.info(f"Formatted Dr.Foodlove prompt: {prompt[:200]}...")
    
    try:
        # Get recommendations using the langflow service
        logger.info("Calling langflow service for recommendations...")
        response = await get_ai_food_recommendations(
            query=prompt,
            user_preferences=None,  # We've already formatted the preferences in our prompt
            limit=limit,
            file_path=food_image_path,
            available_foods=available_foods  # Pass available foods to the langflow service
        )
        
        # Log the raw response for debugging
        logger.info(f"Raw response from langflow service: {json.dumps(response)[:500]}...")
        
        # Add Dr. Foodlove branding to the response
        if response.get("success", False):
            response["provider"] = "Dr. Foodlove AI"
            response["query"] = query  # Use the original query, not our formatted prompt
            
            # Add health insights if detailed response is requested
            if detailed_response and response.get("recommendations"):
                response["health_insights"] = generate_health_insights(
                    query, 
                    response["recommendations"],
                    user_preferences
                )
            
            # Add the full conversation to the response
            if "result" in response:
                response["conversation"] = response["result"]
                
            # Log the number of recommendations
            logger.info(f"Successfully processed {len(response.get('recommendations', []))} recommendations")
        else:
            # Ensure error responses include required fields
            if "query" not in response:
                response["query"] = query
            if "provider" not in response:
                response["provider"] = "Dr. Foodlove AI"
            if "user_preferences_applied" not in response:
                response["user_preferences_applied"] = user_preferences is not None
            
            # Log the error
            logger.error(f"Error in langflow service response: {response.get('error', 'Unknown error')}")
        
        return response
    except Exception as e:
        logger.error(f"Error in Dr. Foodlove service: {e}")
        # Return a properly formatted error response with all required fields
        return {
            "success": False,
            "query": query,
            "provider": "Dr. Foodlove AI",
            "recommendations": [],
            "user_preferences_applied": user_preferences is not None,
            "error": f"Dr. Foodlove service error: {str(e)}"
        }


def generate_health_insights(
    query: str, 
    recommendations: List[Dict[str, Any]],
    user_preferences: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate health insights based on the recommendations and user preferences.
    
    Args:
        query: The user's original query
        recommendations: List of food recommendations
        user_preferences: Optional user preferences
        
    Returns:
        Dictionary containing health insights
    """
    # Extract food types from recommendations
    food_types = []
    nutrients = {"protein": 0, "fiber": 0, "vitamins": []}
    
    for rec in recommendations:
        # Extract cuisine type
        if rec.get("cuisine_type"):
            food_types.append(rec.get("cuisine_type"))
        
        # Extract nutrients from description or nutritional info
        if rec.get("nutritional_info"):
            if isinstance(rec["nutritional_info"], dict):
                if "protein" in rec["nutritional_info"]:
                    nutrients["protein"] += 1
                if "fiber" in rec["nutritional_info"]:
                    nutrients["fiber"] += 1
        
        # Check description for nutrient mentions
        description = rec.get("description", "").lower()
        if "protein" in description:
            nutrients["protein"] += 1
        if "fiber" in description:
            nutrients["fiber"] += 1
        if "vitamin" in description:
            for vitamin in ["a", "b", "c", "d", "e"]:
                if f"vitamin {vitamin}" in description:
                    nutrients["vitamins"].append(vitamin.upper())
    
    # Generate insights
    insights = {
        "variety": len(set(food_types)),
        "nutrient_focus": [],
        "balance_score": min(5, len(set(food_types)) + (nutrients["protein"] > 0) + (nutrients["fiber"] > 0)),
        "recommendations": []
    }
    
    # Add nutrient focus
    if nutrients["protein"] >= 2:
        insights["nutrient_focus"].append("protein")
    if nutrients["fiber"] >= 2:
        insights["nutrient_focus"].append("fiber")
    if len(set(nutrients["vitamins"])) >= 2:
        insights["nutrient_focus"].append("vitamins")
    
    # Add general recommendations
    if insights["balance_score"] < 3:
        insights["recommendations"].append("Consider adding more variety to your meals")
    if "protein" not in insights["nutrient_focus"]:
        insights["recommendations"].append("You might want to include more protein-rich foods")
    if "fiber" not in insights["nutrient_focus"]:
        insights["recommendations"].append("Consider adding more fiber-rich foods for digestive health")
    
    return insights 