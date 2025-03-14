from fastapi import APIRouter, HTTPException, status, Depends, Path, Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, UUID4, Field
from ....core.supabase import execute_query
from ...v1.endpoints.users import get_current_user
from ...v1.endpoints.swaps import SwapStatus

router = APIRouter(prefix="/ratings", tags=["ratings"])

class RatingBase(BaseModel):
    swap_id: UUID4
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=500)

class RatingCreate(RatingBase):
    pass

class RatingResponse(RatingBase):
    id: UUID4
    rater_id: UUID4
    rated_user_id: UUID4
    created_at: datetime

@router.post("/", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
async def create_rating(
    rating: RatingCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Rate a user after a completed swap.
    """
    rater_id = current_user["id"]
    
    # Get the swap
    swap = await execute_query(
        table="swaps",
        query_type="select",
        filters={"id": str(rating.swap_id)}
    )
    
    if not swap or len(swap) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Swap not found"
        )
    
    swap = swap[0]
    
    # Verify the swap is completed
    if swap["status"] != SwapStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can only rate completed swaps"
        )
    
    # Verify the user is part of this swap
    if swap["requester_id"] != rater_id and swap["provider_id"] != rater_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to rate this swap"
        )
    
    # Determine who is being rated
    if swap["requester_id"] == rater_id:
        rated_user_id = swap["provider_id"]
    else:
        rated_user_id = swap["requester_id"]
    
    # Check if the user has already rated this swap
    existing_rating = await execute_query(
        table="ratings",
        query_type="select",
        filters={"swap_id": str(rating.swap_id), "rater_id": rater_id}
    )
    
    if existing_rating and len(existing_rating) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already rated this swap"
        )
    
    # Create rating in database
    rating_data = {
        **rating.model_dump(),
        "rater_id": rater_id,
        "rated_user_id": rated_user_id,
        "created_at": datetime.now().isoformat()
    }
    
    new_rating = await execute_query(
        table="ratings",
        query_type="insert",
        data=rating_data
    )
    
    if not new_rating or len(new_rating) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create rating"
        )
    
    return new_rating[0]

@router.get("/user/{user_id}", response_model=List[RatingResponse])
async def get_user_ratings(
    user_id: UUID4 = Path(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Get all ratings for a specific user.
    """
    # Get ratings from database
    ratings = await execute_query(
        table="ratings",
        query_type="select",
        filters={"rated_user_id": str(user_id)},
        order_by={"created_at": "desc"},
        limit=limit
    )
    
    # Skip the first 'skip' ratings
    return ratings[skip:skip + limit]

@router.get("/swap/{swap_id}", response_model=List[RatingResponse])
async def get_swap_ratings(
    swap_id: UUID4 = Path(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all ratings for a specific swap.
    """
    user_id = current_user["id"]
    
    # Get the swap
    swap = await execute_query(
        table="swaps",
        query_type="select",
        filters={"id": str(swap_id)}
    )
    
    if not swap or len(swap) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Swap not found"
        )
    
    swap = swap[0]
    
    # Verify the user is part of this swap
    if swap["requester_id"] != user_id and swap["provider_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view ratings for this swap"
        )
    
    # Get ratings from database
    ratings = await execute_query(
        table="ratings",
        query_type="select",
        filters={"swap_id": str(swap_id)},
        order_by={"created_at": "desc"}
    )
    
    return ratings 