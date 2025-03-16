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

Please provide {limit} food recommendations that are:
1. Nutritionally balanced
2. Aligned with the user's preferences and restrictions
3. Practical to prepare
4. Varied in cuisine types

For each recommendation, include:
- Name of the dish
- Brief description
- Key ingredients
- Basic preparation instructions
- Nutritional highlights
- Cuisine type
- Any dietary tags (vegetarian, gluten-free, etc.)
"""


async def get_dr_foodlove_recommendations(
    query: str,
    user_preferences: Optional[Dict[str, Any]] = None,
    limit: int = 5,
    food_image_path: Optional[str] = None,
    detailed_response: bool = False
) -> Dict[str, Any]:
    """
    Get personalized food recommendations from Dr. Foodlove AI.
    
    Args:
        query: The user's food query or request
        user_preferences: Optional user preferences to customize recommendations
        limit: Maximum number of recommendations to return
        food_image_path: Optional path to a food image for analysis
        detailed_response: Whether to include detailed nutritional information
        
    Returns:
        Dictionary containing AI recommendations and metadata
    """
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
    
    # Format the prompt
    prompt = DR_FOODLOVE_PROMPT_TEMPLATE.format(
        query=query,
        preferences_section=preferences_section,
        limit=limit
    )
    
    # Get recommendations using the langflow service
    response = await get_ai_food_recommendations(
        query=prompt,
        user_preferences=None,  # We've already formatted the preferences in our prompt
        limit=limit,
        file_path=food_image_path
    )
    
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
    
    return response


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