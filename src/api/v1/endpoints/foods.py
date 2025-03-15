from fastapi import APIRouter, HTTPException, status, Query, Path, Depends
from typing import List, Optional
from datetime import datetime
from pydantic import UUID4
from ....schemas.food import FoodCreate, FoodResponse, FoodUpdate, FoodCategory, FoodType
from ....schemas.user import DietaryRequirement
from ...v1.endpoints.users import get_current_user
from ....core.supabase import execute_query

router = APIRouter(prefix="/foods", tags=["foods"])

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