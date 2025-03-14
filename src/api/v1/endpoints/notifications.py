from fastapi import APIRouter, HTTPException, status, Depends, Path, Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, UUID4
from enum import Enum
from ....core.supabase import execute_query
from ...v1.endpoints.users import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])

class NotificationType(str, Enum):
    SWAP_REQUEST = "swap_request"
    SWAP_ACCEPTED = "swap_accepted"
    SWAP_REJECTED = "swap_rejected"
    SWAP_COMPLETED = "swap_completed"
    FOOD_EXPIRING = "food_expiring"
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