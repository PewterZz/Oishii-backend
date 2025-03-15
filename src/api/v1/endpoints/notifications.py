from fastapi import APIRouter, HTTPException, status, Depends, Path, Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, UUID4
from enum import Enum
from ....core.supabase import execute_query, execute_raw_sql
from ...v1.endpoints.users import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])

class NotificationType(str, Enum):
    SWAP_REQUEST = "swap_request"
    SWAP_ACCEPTED = "swap_accepted"
    SWAP_REJECTED = "swap_rejected"
    SWAP_COMPLETED = "swap_completed"
    FOOD_EXPIRING = "food_expiring"
    NEARBY_FOOD = "nearby_food"
    NEARBY_USER = "nearby_user"
    SYSTEM = "system"

class NotificationBase(BaseModel):
    type: NotificationType
    title: str
    message: str
    related_id: Optional[UUID4] = None
    is_read: bool = False

class NotificationCreate(NotificationBase):
    user_id: UUID4

class NotificationUpdate(BaseModel):
    is_read: bool

class NotificationResponse(NotificationBase):
    id: UUID4
    user_id: UUID4
    created_at: datetime

@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    is_read: Optional[bool] = None,
    type: Optional[NotificationType] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all notifications for the current user with optional filtering.
    """
    user_id = current_user["id"]
    
    # Build filters
    filters = {"user_id": user_id}
    
    if is_read is not None:
        filters["is_read"] = is_read
    
    if type:
        filters["type"] = type.value
    
    # Get notifications from database
    notifications = await execute_query(
        table="notifications",
        query_type="select",
        filters=filters,
        order_by={"created_at": "desc"},
        limit=limit
    )
    
    # Skip the first 'skip' notifications
    return notifications[skip:skip + limit]

@router.patch("/{notification_id}", response_model=NotificationResponse)
async def mark_notification(
    notification_update: NotificationUpdate,
    notification_id: UUID4 = Path(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Mark a notification as read or unread.
    """
    user_id = current_user["id"]
    
    # Get notification from database
    notification = await execute_query(
        table="notifications",
        query_type="select",
        filters={"id": str(notification_id)}
    )
    
    if not notification or len(notification) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification = notification[0]
    
    # Verify the user owns this notification
    if notification["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this notification"
        )
    
    # Update notification in database
    updated_notification = await execute_query(
        table="notifications",
        query_type="update",
        filters={"id": str(notification_id)},
        data={"is_read": notification_update.is_read}
    )
    
    if not updated_notification or len(updated_notification) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification"
        )
    
    return updated_notification[0]

@router.patch("/", response_model=List[NotificationResponse])
async def mark_all_notifications(
    notification_update: NotificationUpdate,
    type: Optional[NotificationType] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark all notifications as read or unread.
    """
    user_id = current_user["id"]
    
    # Build filters
    filters = {"user_id": user_id}
    
    if type:
        filters["type"] = type.value
    
    # Update notifications in database
    updated_notifications = await execute_query(
        table="notifications",
        query_type="update",
        filters=filters,
        data={"is_read": notification_update.is_read}
    )
    
    if not updated_notifications:
        # No notifications to update
        return []
    
    return updated_notifications

@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: UUID4 = Path(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a notification.
    """
    user_id = current_user["id"]
    
    # Get notification from database
    notification = await execute_query(
        table="notifications",
        query_type="select",
        filters={"id": str(notification_id)}
    )
    
    if not notification or len(notification) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification = notification[0]
    
    # Verify the user owns this notification
    if notification["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this notification"
        )
    
    # Delete notification from database
    await execute_query(
        table="notifications",
        query_type="delete",
        filters={"id": str(notification_id)}
    )
    
    return None

@router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    notification: NotificationCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new notification (admin only in a real app).
    """
    # In a real app, we would check if the current user is an admin
    
    # Create notification in database
    notification_data = {
        **notification.model_dump(),
        "created_at": datetime.now().isoformat()
    }
    
    new_notification = await execute_query(
        table="notifications",
        query_type="insert",
        data=notification_data
    )
    
    if not new_notification or len(new_notification) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create notification"
        )
    
    return new_notification[0]

@router.post("/nearby-foods", status_code=status.HTTP_201_CREATED)
async def create_nearby_food_notifications(
    radius: float = Query(5.0, description="Search radius in kilometers", ge=0.1, le=50.0),
    current_user: dict = Depends(get_current_user)
):
    """
    Create notifications for new foods available near the current user's location.
    
    This endpoint scans for foods within the specified radius (in kilometers)
    of the current user's location and creates notifications for new foods.
    """
    try:
        # Get the current user's location
        user_result = await execute_query(
            table="users",
            query_type="select",
            filters={"id": current_user["id"]}
        )
        
        if not user_result or len(user_result) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_location = user_result[0].get("location")
        
        if not user_location:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User location not set"
            )
        
        # Find nearby users
        nearby_users_query = """
        SELECT id
        FROM users
        WHERE id != %s
        AND location IS NOT NULL
        AND ST_DWithin(
            ST_SetSRID(ST_MakePoint(
                (location->>'longitude')::float,
                (location->>'latitude')::float
            ), 4326)::geography,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
            %s
        )
        """
        
        nearby_users_params = [
            current_user["id"],
            user_location["longitude"],
            user_location["latitude"],
            radius * 1000  # Convert km to meters
        ]
        
        nearby_users_result = await execute_raw_sql(nearby_users_query, nearby_users_params)
        
        if not nearby_users_result or "data" not in nearby_users_result or len(nearby_users_result["data"]) == 0:
            return {"message": "No nearby users found"}
        
        # Extract user IDs
        nearby_user_ids = [user["id"] for user in nearby_users_result["data"]]
        
        # Find foods from nearby users that were created in the last 24 hours
        foods_query = """
        SELECT f.*, u.first_name, u.last_name
        FROM foods f
        JOIN users u ON f.user_id = u.id
        WHERE f.user_id = ANY(%s)
        AND f.is_available = true
        AND f.created_at > NOW() - INTERVAL '24 hours'
        """
        
        foods_params = [nearby_user_ids]
        
        foods_result = await execute_raw_sql(foods_query, foods_params)
        
        if not foods_result or "data" not in foods_result or len(foods_result["data"]) == 0:
            return {"message": "No new nearby foods found"}
        
        # Check if notifications already exist for these foods
        notifications_created = 0
        
        for food in foods_result["data"]:
            # Check if notification already exists
            existing_notification = await execute_query(
                table="notifications",
                query_type="select",
                filters={
                    "user_id": current_user["id"],
                    "type": "nearby_food",
                    "related_id": food["id"]
                }
            )
            
            if existing_notification and len(existing_notification) > 0:
                # Notification already exists, skip
                continue
            
            # Create notification
            notification_data = {
                "user_id": current_user["id"],
                "type": "nearby_food",
                "title": "New Food Nearby",
                "message": f"{food['first_name']} {food['last_name']} added {food['name']} near you!",
                "related_id": food["id"],
                "is_read": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            await execute_query(
                table="notifications",
                query_type="insert",
                data=notification_data
            )
            
            notifications_created += 1
        
        return {
            "message": f"Created {notifications_created} new notifications for nearby foods",
            "count": notifications_created
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 