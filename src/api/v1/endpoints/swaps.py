from fastapi import APIRouter, HTTPException, status, Depends, Path, Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, UUID4
from enum import Enum
from ....core.supabase import execute_query
from ...v1.endpoints.users import get_current_user

router = APIRouter(prefix="/swaps", tags=["swaps"])

class SwapStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"

class SwapCreate(BaseModel):
    provider_id: UUID4
    provider_food_id: UUID4
    requester_food_id: UUID4
    message: Optional[str] = None

class SwapUpdate(BaseModel):
    status: SwapStatus
    response_message: Optional[str] = None

class SwapResponse(BaseModel):
    id: UUID4
    requester_id: UUID4
    provider_id: UUID4
    requester_food_id: UUID4
    provider_food_id: UUID4
    message: Optional[str] = None
    response_message: Optional[str] = None
    status: SwapStatus
    created_at: datetime
    updated_at: datetime

class SwapDetailResponse(BaseModel):
    id: UUID4
    requester_id: UUID4
    provider_id: UUID4
    requester_food_id: UUID4
    provider_food_id: UUID4
    message: Optional[str] = None
    response_message: Optional[str] = None
    status: SwapStatus
    created_at: datetime
    updated_at: datetime
    requester_food: dict
    provider_food: dict

@router.post("/", response_model=SwapResponse, status_code=status.HTTP_201_CREATED)
async def create_swap_request(
    swap: SwapCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new swap request.
    
    This endpoint allows a user to request a food swap with another user.
    The requester must own the requester_food_id and the provider must own the provider_food_id.
    """
    # Verify user is verified
    if not current_user.get("is_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must verify your email before creating swap requests"
        )
    
    requester_id = current_user["id"]
    
    # Verify the requester food belongs to the requester
    requester_food = await execute_query(
        table="foods",
        query_type="select",
        filters={"id": str(swap.requester_food_id)}
    )
    
    if not requester_food or len(requester_food) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requester food not found"
        )
    
    requester_food = requester_food[0]
    
    if requester_food["user_id"] != requester_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't own this food item"
        )
    
    # Verify the provider food exists and is available
    provider_food = await execute_query(
        table="foods",
        query_type="select",
        filters={"id": str(swap.provider_food_id)}
    )
    
    if not provider_food or len(provider_food) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider food not found"
        )
    
    provider_food = provider_food[0]
    
    if not provider_food["is_available"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This food item is not available for swapping"
        )
    
    # Verify the provider exists
    provider = await execute_query(
        table="users",
        query_type="select",
        filters={"id": str(swap.provider_id)}
    )
    
    if not provider or len(provider) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    provider = provider[0]
    
    # Verify the provider owns the provider food
    if provider_food["user_id"] != provider["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The provider does not own this food item"
        )
    
    # Create swap in database
    now = datetime.now().isoformat()
    swap_data = {
        "requester_id": requester_id,
        "provider_id": str(swap.provider_id),
        "requester_food_id": str(swap.requester_food_id),
        "provider_food_id": str(swap.provider_food_id),
        "message": swap.message,
        "status": SwapStatus.PENDING.value,
        "created_at": now,
        "updated_at": now
    }
    
    new_swap = await execute_query(
        table="swaps",
        query_type="insert",
        data=swap_data
    )
    
    if not new_swap or len(new_swap) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create swap request"
        )
    
    # Create notification for the provider
    notification_data = {
        "user_id": str(swap.provider_id),
        "title": "New Swap Request",
        "message": f"You have a new swap request from {current_user.get('first_name', 'a user')}",
        "type": "swap_request",
        "is_read": False,
        "data": {"swap_id": new_swap[0]["id"]},
        "created_at": now,
        "updated_at": now
    }
    
    await execute_query(
        table="notifications",
        query_type="insert",
        data=notification_data
    )
    
    return new_swap[0]

@router.get("/", response_model=List[SwapResponse])
async def get_swaps(
    status: Optional[SwapStatus] = None,
    role: Optional[str] = Query(None, regex="^(requester|provider)$"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all swaps for the current user with optional filtering.
    """
    user_id = current_user["id"]
    
    # Build filters based on role
    filters = {}
    
    if role == "requester":
        filters["requester_id"] = user_id
    elif role == "provider":
        filters["provider_id"] = user_id
    else:
        # If no role specified, get all swaps where the user is either requester or provider
        # This is a bit more complex and requires post-filtering
        pass
    
    if status:
        filters["status"] = status.value
    
    # Get swaps from database
    swaps = await execute_query(
        table="swaps",
        query_type="select",
        filters=filters
    )
    
    # If no role specified, filter after the query
    if not role:
        swaps = [
            swap for swap in swaps 
            if swap["requester_id"] == user_id or swap["provider_id"] == user_id
        ]
    
    return swaps

@router.get("/{swap_id}", response_model=SwapResponse)
async def get_swap(
    swap_id: UUID4 = Path(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific swap by ID.
    """
    user_id = current_user["id"]
    
    # Get swap from database
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
            detail="You don't have permission to view this swap"
        )
    
    return swap

@router.patch("/{swap_id}", response_model=SwapResponse)
async def update_swap_status(
    swap_update: SwapUpdate,
    swap_id: UUID4 = Path(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a swap status (accept, reject, complete).
    """
    user_id = current_user["id"]
    
    # Get swap from database
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
            detail="You don't have permission to update this swap"
        )
    
    # Check valid status transitions
    current_status = swap["status"]
    new_status = swap_update.status.value
    
    # Only the provider can accept or reject a swap
    if new_status in [SwapStatus.ACCEPTED.value, SwapStatus.REJECTED.value]:
        if swap["provider_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the provider can accept or reject a swap"
            )
        
        if current_status != SwapStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot change status from {current_status} to {new_status}"
            )
    
    # Both users can mark a swap as completed, but only if it's accepted
    if new_status == SwapStatus.COMPLETED.value:
        if current_status != SwapStatus.ACCEPTED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot change status from {current_status} to {new_status}"
            )
    
    # Update swap in database
    update_data = {
        "status": new_status,
        "updated_at": datetime.now().isoformat()
    }
    
    if swap_update.response_message:
        update_data["response_message"] = swap_update.response_message
    
    updated_swap = await execute_query(
        table="swaps",
        query_type="update",
        filters={"id": str(swap_id)},
        data=update_data
    )
    
    if not updated_swap or len(updated_swap) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update swap"
        )
    
    # If the swap is accepted, mark both food items as unavailable
    if new_status == SwapStatus.ACCEPTED.value:
        await execute_query(
            table="foods",
            query_type="update",
            filters={"id": swap["requester_food_id"]},
            data={"is_available": False, "updated_at": datetime.now().isoformat()}
        )
        
        await execute_query(
            table="foods",
            query_type="update",
            filters={"id": swap["provider_food_id"]},
            data={"is_available": False, "updated_at": datetime.now().isoformat()}
        )
    
    return updated_swap[0]

@router.get("/{swap_id}/detail", response_model=SwapDetailResponse)
async def get_swap_detail(
    swap_id: UUID4 = Path(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed information about a specific swap, including the food details.
    """
    user_id = current_user["id"]
    
    # Get swap from database
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
            detail="You don't have permission to view this swap"
        )
    
    # Get requester food details
    requester_food = await execute_query(
        table="foods",
        query_type="select",
        filters={"id": swap["requester_food_id"]}
    )
    
    if not requester_food or len(requester_food) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requester food not found"
        )
    
    # Get provider food details
    provider_food = await execute_query(
        table="foods",
        query_type="select",
        filters={"id": swap["provider_food_id"]}
    )
    
    if not provider_food or len(provider_food) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider food not found"
        )
    
    # Add food details to swap
    swap_detail = {
        **swap,
        "requester_food": requester_food[0],
        "provider_food": provider_food[0]
    }
    
    return swap_detail 