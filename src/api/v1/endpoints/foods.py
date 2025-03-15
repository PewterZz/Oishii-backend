from fastapi import APIRouter, HTTPException, status, Query, Path, Depends
from typing import List, Optional
from datetime import datetime
from pydantic import UUID4
from ....schemas.food import FoodCreate, FoodResponse, FoodUpdate, FoodCategory, FoodType
from ....schemas.user import DietaryRequirement
from ...v1.endpoints.users import get_current_user
from ....core.supabase import execute_query

router = APIRouter(tags=["foods"])

@router.post("/", response_model=FoodResponse, status_code=status.HTTP_201_CREATED)
async def create_food(
    food: FoodCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new food listing.
    
    This can be either an offering (a meal being shared) or a request (a meal being requested).
    For offerings, you can specify how many tickets are required to claim it.
    For requests, you can specify how many tickets you're willing to pay.
    """
    # Verify user is verified
    if not current_user.get("is_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must verify your email before creating food listings"
        )
    
    user_id = current_user["id"]
    
    # Create food in database
    now = datetime.now().isoformat()
    food_data = {
        **food.model_dump(),
        "user_id": user_id,
        "created_at": now,
        "updated_at": now
    }
    
    # Ensure pickup_times is included
    if food_data.get("pickup_times") is None:
        food_data["pickup_times"] = []
    
    # Ensure tickets_required is included and valid
    if food_data.get("tickets_required") is None:
        food_data["tickets_required"] = 1
    
    new_food = await execute_query(
        table="foods",
        query_type="insert",
        data=food_data
    )
    
    if not new_food or len(new_food) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create food listing"
        )
    
    return new_food[0]

@router.get("/", response_model=List[FoodResponse])
async def get_foods(
    category: Optional[FoodCategory] = None,
    food_type: Optional[FoodType] = None,
    dietary_requirement: Optional[DietaryRequirement] = None,
    is_available: Optional[bool] = None,
    is_homemade: Optional[bool] = None,
    location: Optional[str] = None,
    allergen_free: Optional[str] = None,
    search: Optional[str] = None,
    max_tickets: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Get all food listings with optional filtering.
    
    You can filter by:
    - category (meal, snack, dessert, etc.)
    - food_type (offering or request)
    - dietary requirements
    - availability
    - homemade status
    - location
    - allergen-free
    - search term
    - maximum tickets required
    """
    # Build filters
    filters = {}
    
    if category:
        filters["category"] = category.value
    
    if food_type:
        filters["food_type"] = food_type.value
    
    if is_available is not None:
        filters["is_available"] = is_available
    
    if is_homemade is not None:
        filters["is_homemade"] = is_homemade
    
    # Get foods from database
    foods = await execute_query(
        table="foods",
        query_type="select",
        filters=filters,
        limit=limit
    )
    
    # Apply additional filtering that can't be done directly in the query
    filtered_foods = foods
    
    # Filter by dietary requirement
    if dietary_requirement:
        filtered_foods = [
            food for food in filtered_foods 
            if dietary_requirement.value in food["dietary_requirements"]
        ]
    
    # Filter by location
    if location:
        filtered_foods = [
            food for food in filtered_foods 
            if location.lower() in food["location"].lower()
        ]
    
    # Filter by allergen-free
    if allergen_free:
        allergen_free_lower = allergen_free.lower()
        filtered_foods = [
            food for food in filtered_foods 
            if allergen_free_lower not in food["allergens"].lower()
        ]
    
    # Filter by search term
    if search:
        search = search.lower()
        filtered_foods = [
            food for food in filtered_foods 
            if search in food["title"].lower() or search in food["description"].lower()
        ]
    
    # Filter by maximum tickets required
    if max_tickets is not None:
        filtered_foods = [
            food for food in filtered_foods 
            if food.get("tickets_required", 1) <= max_tickets
        ]
    
    # Skip the first 'skip' foods
    return filtered_foods[skip:skip + limit]

@router.get("/nearby", response_model=List[FoodResponse])
async def get_nearby_foods(
    location: str = Query(..., min_length=3),
    distance: float = Query(5.0, gt=0),  # Default 5km radius
    category: Optional[FoodCategory] = None,
    dietary_requirement: Optional[DietaryRequirement] = None,
    allergen_free: Optional[str] = None,
    is_available: Optional[bool] = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Get food listings near a specific location.
    In a real app, this would use geolocation coordinates and calculate actual distances.
    For demo purposes, we'll just filter by location string.
    """
    # Build filters
    filters = {}
    
    if is_available is not None:
        filters["is_available"] = is_available
    
    if category:
        filters["category"] = category.value
    
    # Get foods from database
    foods = await execute_query(
        table="foods",
        query_type="select",
        filters=filters
    )
    
    # Filter by location (simple string matching for demo)
    filtered_foods = [
        food for food in foods 
        if location.lower() in food["location"].lower()
    ]
    
    # Filter by dietary requirement
    if dietary_requirement:
        filtered_foods = [
            food for food in filtered_foods 
            if dietary_requirement.value in food["dietary_requirements"]
        ]
    
    # Filter by allergen-free
    if allergen_free:
        allergen_free_lower = allergen_free.lower()
        filtered_foods = [
            food for food in filtered_foods 
            if allergen_free_lower not in food["allergens"].lower()
        ]
    
    # Skip the first 'skip' foods
    return filtered_foods[skip:skip + limit]

@router.get("/{food_id}", response_model=FoodResponse)
async def get_food(food_id: UUID4 = Path(...)):
    """
    Get a specific food listing by ID.
    """
    food = await execute_query(
        table="foods",
        query_type="select",
        filters={"id": str(food_id)}
    )
    
    if not food or len(food) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food not found"
        )
    
    return food[0]

@router.patch("/{food_id}", response_model=FoodResponse)
async def update_food(
    food_update: FoodUpdate,
    food_id: UUID4 = Path(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a food listing.
    """
    # Get food from database
    food = await execute_query(
        table="foods",
        query_type="select",
        filters={"id": str(food_id)}
    )
    
    if not food or len(food) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food not found"
        )
    
    food = food[0]
    
    # Verify the user owns this food listing
    if food["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this food listing"
        )
    
    # Update food in database
    update_data = food_update.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now().isoformat()
    
    updated_food = await execute_query(
        table="foods",
        query_type="update",
        filters={"id": str(food_id)},
        data=update_data
    )
    
    if not updated_food or len(updated_food) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update food listing"
        )
    
    return updated_food[0]

@router.delete("/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_food(
    food_id: UUID4 = Path(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a food listing.
    """
    # Get food from database
    food = await execute_query(
        table="foods",
        query_type="select",
        filters={"id": str(food_id)}
    )
    
    if not food or len(food) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food not found"
        )
    
    food = food[0]
    
    # Verify the user owns this food listing
    if food["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this food listing"
        )
    
    # Delete food from database
    await execute_query(
        table="foods",
        query_type="delete",
        filters={"id": str(food_id)}
    )
    
    return None

@router.get("/user/{user_id}", response_model=List[FoodResponse])
async def get_user_foods(
    user_id: UUID4 = Path(...),
    is_available: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Get all food listings for a specific user.
    """
    # Build filters
    filters = {"user_id": str(user_id)}
    
    if is_available is not None:
        filters["is_available"] = is_available
    
    # Get foods from database
    foods = await execute_query(
        table="foods",
        query_type="select",
        filters=filters,
        limit=limit
    )
    
    # Skip the first 'skip' foods
    return foods[skip:skip + limit]

@router.post("/{food_id}/fulfill", response_model=FoodResponse)
async def fulfill_food_request(
    food_id: UUID4 = Path(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Fulfill a food request by offering to make the requested meal.
    
    This endpoint is used when a student wants to fulfill another student's food request.
    The student who fulfills the request will earn the tickets specified in the request.
    """
    user_id = current_user["id"]
    
    # Get food request from database
    food = await execute_query(
        table="foods",
        query_type="select",
        filters={"id": str(food_id)}
    )
    
    if not food or len(food) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food request not found"
        )
    
    food = food[0]
    
    # Check if this is a request type food
    if food.get("food_type") != "request":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not a food request"
        )
    
    # Check if food request is still available
    if not food["is_available"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This food request is no longer available"
        )
    
    # Check if user is trying to fulfill their own request
    if food["user_id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot fulfill your own food request"
        )
    
    # Update food request status
    now = datetime.now().isoformat()
    updated_food = await execute_query(
        table="foods",
        query_type="update",
        filters={"id": str(food_id)},
        data={
            "is_available": False, 
            "fulfilled_by": user_id,
            "fulfilled_at": now,
            "updated_at": now
        }
    )
    
    if not updated_food or len(updated_food) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update food request"
        )
    
    # Create fulfillment record
    fulfillment_data = {
        "food_id": str(food_id),
        "requester_id": food["user_id"],
        "provider_id": user_id,
        "tickets_earned": food.get("tickets_required", 1),
        "status": "accepted",
        "created_at": now,
        "updated_at": now
    }
    
    await execute_query(
        table="food_fulfillments",
        query_type="insert",
        data=fulfillment_data
    )
    
    # Create notification for the requester
    notification_data = {
        "user_id": food["user_id"],
        "title": "Food Request Fulfilled",
        "message": f"Your food request '{food['title']}' has been fulfilled by {current_user.get('first_name', 'a user')}",
        "type": "request_fulfilled",
        "is_read": False,
        "data": {"food_id": str(food_id)},
        "created_at": now,
        "updated_at": now
    }
    
    await execute_query(
        table="notifications",
        query_type="insert",
        data=notification_data
    )
    
    return updated_food[0]

@router.get("/search/personalized", response_model=List[FoodResponse])
async def search_personalized_foods(
    search_term: Optional[str] = Query(None, min_length=2),
    current_user: dict = Depends(get_current_user),
    food_type: Optional[FoodType] = None,
    category: Optional[FoodCategory] = None,
    max_distance: float = Query(5.0, gt=0),  # Default 5km radius
    max_tickets: Optional[int] = None,
    is_available: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Search for food listings personalized to the current user's preferences and dietary restrictions.
    
    This endpoint automatically considers:
    - User's dietary requirements
    - User's allergen restrictions
    - User's location for proximity
    - User's preferred food categories (if set in profile)
    
    Additional filters can be applied through query parameters.
    """
    user_id = current_user["id"]
    user_location = current_user.get("home_address", "")
    user_dietary_requirements = current_user.get("dietary_requirements", [])
    user_allergies = current_user.get("allergies", "").lower()
    
    # Build base filters
    filters = {"is_available": is_available}
    
    # Don't show user's own food in personalized search
    filters["user_id"] = {"neq": user_id}
    
    if food_type:
        filters["food_type"] = food_type.value
    
    if category:
        filters["category"] = category.value
    
    # Get foods from database
    foods = await execute_query(
        table="foods",
        query_type="select",
        filters=filters
    )
    
    # Apply personalized filtering
    personalized_foods = []
    
    for food in foods:
        # Skip if the food contains allergens the user is allergic to
        if user_allergies:
            food_allergens = food.get("allergens", "").lower()
            # Check if any of the user's allergies are in the food's allergens
            allergen_match = False
            for allergen in user_allergies.split(","):
                allergen = allergen.strip()
                if allergen and allergen in food_allergens:
                    allergen_match = True
                    break
            
            if allergen_match:
                continue
        
        # Calculate match score (higher is better)
        match_score = 0
        
        # Location proximity match
        if user_location and food.get("location"):
            # Simple string matching for demo
            # In a real app, this would use geolocation distance calculation
            if user_location.lower() in food.get("location", "").lower():
                match_score += 3
        
        # Dietary requirements match
        food_dietary = food.get("dietary_requirements", [])
        for req in user_dietary_requirements:
            if req in food_dietary:
                match_score += 2
        
        # Search term match
        if search_term:
            search_term_lower = search_term.lower()
            if search_term_lower in food.get("title", "").lower():
                match_score += 5  # Title match is highly relevant
            elif search_term_lower in food.get("description", "").lower():
                match_score += 3  # Description match is relevant
            elif search_term_lower in food.get("category", "").lower():
                match_score += 2  # Category match is somewhat relevant
        else:
            # If no search term, give a small boost to all results
            match_score += 1
        
        # Ticket affordability match
        if max_tickets is not None:
            tickets_required = food.get("tickets_required", 1)
            if tickets_required <= max_tickets:
                match_score += 1
                # Extra points for free or very cheap items
                if tickets_required <= 1:
                    match_score += 1
        
        # Add match score to food item
        food["match_score"] = match_score
        personalized_foods.append(food)
    
    # Sort by match score (highest first)
    personalized_foods.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    
    # Apply skip and limit
    paginated_foods = personalized_foods[skip:skip + limit]
    
    # Remove match_score before returning (it's not in the schema)
    for food in paginated_foods:
        if "match_score" in food:
            del food["match_score"]
    
    return paginated_foods

@router.get("/search/requests", response_model=List[FoodResponse])
async def search_food_requests(
    search_term: Optional[str] = Query(None, min_length=2),
    current_user: dict = Depends(get_current_user),
    category: Optional[FoodCategory] = None,
    min_tickets: Optional[int] = None,
    max_distance: float = Query(5.0, gt=0),
    is_available: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Search for food requests that match a user's cooking skills and preferences.
    
    This endpoint helps users find food requests they might want to fulfill based on:
    - Their cooking preferences (from user profile)
    - Location proximity
    - Ticket rewards
    - Food categories they're comfortable with
    
    Results are sorted by relevance to the user's skills and preferences.
    """
    user_id = current_user["id"]
    user_location = current_user.get("home_address", "")
    user_cook_type = current_user.get("cook_type", "").lower()
    user_cook_frequency = current_user.get("cook_frequency", "").lower()
    
    # Build base filters
    filters = {
        "is_available": is_available,
        "food_type": "request"  # Only show food requests
    }
    
    # Don't show user's own requests
    filters["user_id"] = {"neq": user_id}
    
    if category:
        filters["category"] = category.value
    
    # Get food requests from database
    food_requests = await execute_query(
        table="foods",
        query_type="select",
        filters=filters
    )
    
    # Apply personalized filtering
    matched_requests = []
    
    for request in food_requests:
        # Calculate match score (higher is better)
        match_score = 0
        
        # Location proximity match
        if user_location and request.get("location"):
            # Simple string matching for demo
            if user_location.lower() in request.get("location", "").lower():
                match_score += 3
        
        # Search term match
        if search_term:
            search_term_lower = search_term.lower()
            if search_term_lower in request.get("title", "").lower():
                match_score += 5  # Title match is highly relevant
            elif search_term_lower in request.get("description", "").lower():
                match_score += 3  # Description match is relevant
            elif search_term_lower in request.get("category", "").lower():
                match_score += 2  # Category match is somewhat relevant
        else:
            # If no search term, give a small boost to all results
            match_score += 1
        
        # Ticket reward match
        tickets_offered = request.get("tickets_required", 1)
        if min_tickets is not None and tickets_offered >= min_tickets:
            match_score += 2
            # Extra points for high-reward requests
            if tickets_offered >= 3:
                match_score += 2
        
        # Cooking type match (if user has specified their cooking type)
        if user_cook_type:
            request_description = request.get("description", "").lower()
            # Check if the request description mentions cooking styles that match the user's preferences
            if "meal prep" in request_description and "meal prepper" in user_cook_type:
                match_score += 3
            elif "baking" in request_description and "baker" in user_cook_type:
                match_score += 3
            elif "gourmet" in request_description and "gourmet" in user_cook_type:
                match_score += 3
            elif "quick" in request_description and "quick" in user_cook_type:
                match_score += 3
        
        # Cooking frequency match
        if user_cook_frequency:
            # Higher scores for users who cook frequently
            if "daily" in user_cook_frequency or "5+" in user_cook_frequency:
                match_score += 2
            elif "3-4" in user_cook_frequency:
                match_score += 1
        
        # Add match score to request item
        request["match_score"] = match_score
        matched_requests.append(request)
    
    # Sort by match score (highest first)
    matched_requests.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    
    # Apply skip and limit
    paginated_requests = matched_requests[skip:skip + limit]
    
    # Remove match_score before returning (it's not in the schema)
    for request in paginated_requests:
        if "match_score" in request:
            del request["match_score"]
    
    return paginated_requests

@router.get("/recommendations", response_model=List[FoodResponse])
async def get_food_recommendations(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=20),
    include_requests: bool = Query(False)
):
    """
    Get personalized food recommendations for the current user.
    
    This endpoint analyzes:
    - User's past claims and interactions
    - User's dietary preferences
    - User's location
    - Popular items among similar users
    
    Returns a curated list of recommended food offerings or requests.
    """
    user_id = current_user["id"]
    user_location = current_user.get("home_address", "")
    user_dietary_requirements = current_user.get("dietary_requirements", [])
    user_allergies = current_user.get("allergies", "").lower()
    
    # Get user's past interactions (claims, fulfillments)
    past_claims = await execute_query(
        table="food_claims",
        query_type="select",
        filters={"claimer_id": user_id},
        limit=20
    )
    
    past_fulfillments = await execute_query(
        table="food_fulfillments",
        query_type="select",
        filters={"provider_id": user_id},
        limit=20
    )
    
    # Extract food IDs from past interactions
    past_food_ids = []
    past_provider_ids = []
    past_categories = set()
    
    for claim in past_claims:
        if claim.get("food_id"):
            past_food_ids.append(claim["food_id"])
        if claim.get("provider_id"):
            past_provider_ids.append(claim["provider_id"])
    
    # Get details of past claimed foods to analyze preferences
    if past_food_ids:
        past_foods = await execute_query(
            table="foods",
            query_type="select",
            filters={"id": {"in": past_food_ids}}
        )
        
        for food in past_foods:
            if food.get("category"):
                past_categories.add(food["category"])
    
    # Build filters for recommendations
    filters = {"is_available": True}
    
    # Don't show user's own food
    filters["user_id"] = {"neq": user_id}
    
    # Filter by food type if specified
    if not include_requests:
        filters["food_type"] = "offering"
    
    # Get potential recommendations
    potential_recommendations = await execute_query(
        table="foods",
        query_type="select",
        filters=filters,
        limit=50  # Get more than needed for filtering
    )
    
    # Score and rank recommendations
    scored_recommendations = []
    
    for food in potential_recommendations:
        # Skip if the food contains allergens the user is allergic to
        if user_allergies:
            food_allergens = food.get("allergens", "").lower()
            allergen_match = False
            for allergen in user_allergies.split(","):
                allergen = allergen.strip()
                if allergen and allergen in food_allergens:
                    allergen_match = True
                    break
            
            if allergen_match:
                continue
        
        # Calculate recommendation score
        rec_score = 0
        
        # Preferred category match
        if food.get("category") in past_categories:
            rec_score += 3
        
        # Preferred provider match
        if food.get("user_id") in past_provider_ids:
            rec_score += 4  # Strong signal - user liked this provider before
        
        # Location proximity match
        if user_location and food.get("location"):
            if user_location.lower() in food.get("location", "").lower():
                rec_score += 2
        
        # Dietary requirements match
        food_dietary = food.get("dietary_requirements", [])
        for req in user_dietary_requirements:
            if req in food_dietary:
                rec_score += 1
        
        # Freshness boost (newer items ranked higher)
        if food.get("created_at"):
            try:
                created_at = datetime.fromisoformat(food["created_at"].replace("Z", "+00:00"))
                now = datetime.now()
                age_hours = (now - created_at).total_seconds() / 3600
                
                if age_hours < 24:
                    rec_score += 2  # Posted in last 24 hours
                elif age_hours < 48:
                    rec_score += 1  # Posted in last 48 hours
            except (ValueError, TypeError):
                pass
        
        # Add recommendation score to food item
        food["rec_score"] = rec_score
        scored_recommendations.append(food)
    
    # Sort by recommendation score (highest first)
    scored_recommendations.sort(key=lambda x: x.get("rec_score", 0), reverse=True)
    
    # Take top recommendations up to limit
    top_recommendations = scored_recommendations[:limit]
    
    # Remove recommendation score before returning
    for food in top_recommendations:
        if "rec_score" in food:
            del food["rec_score"]
    
    return top_recommendations 