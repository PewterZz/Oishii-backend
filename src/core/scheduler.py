import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .supabase import execute_query, execute_raw_sql

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("scheduler")

async def check_nearby_foods():
    """
    Check for new foods near users and create notifications.
    
    This task runs periodically to find new foods within a certain radius
    of each user's location and creates notifications for them.
    """
    try:
        logger.info("Starting nearby foods check")
        
        # Get all users with location set
        users_result = await execute_query(
            table="users",
            query_type="select",
            filters={"location": {"$ne": None}}
        )
        
        if not users_result or len(users_result) == 0:
            logger.info("No users with location found")
            return
        
        logger.info(f"Found {len(users_result)} users with location")
        
        # Default radius in kilometers
        radius = 5.0
        
        # Process each user
        for user in users_result:
            try:
                user_id = user["id"]
                user_location = user.get("location")
                
                if not user_location:
                    continue
                
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
                    user_id,
                    user_location["longitude"],
                    user_location["latitude"],
                    radius * 1000  # Convert km to meters
                ]
                
                nearby_users_result = await execute_raw_sql(nearby_users_query, nearby_users_params)
                
                if not nearby_users_result or "data" not in nearby_users_result or len(nearby_users_result["data"]) == 0:
                    logger.info(f"No nearby users found for user {user_id}")
                    continue
                
                # Extract user IDs
                nearby_user_ids = [nearby_user["id"] for nearby_user in nearby_users_result["data"]]
                
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
                    logger.info(f"No new nearby foods found for user {user_id}")
                    continue
                
                # Create notifications for new foods
                notifications_created = 0
                
                for food in foods_result["data"]:
                    # Check if notification already exists
                    existing_notification = await execute_query(
                        table="notifications",
                        query_type="select",
                        filters={
                            "user_id": user_id,
                            "type": "nearby_food",
                            "related_id": food["id"]
                        }
                    )
                    
                    if existing_notification and len(existing_notification) > 0:
                        # Notification already exists, skip
                        continue
                    
                    # Create notification
                    notification_data = {
                        "user_id": user_id,
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
                
                logger.info(f"Created {notifications_created} notifications for user {user_id}")
                
            except Exception as user_error:
                logger.error(f"Error processing user {user.get('id')}: {str(user_error)}")
                continue
        
        logger.info("Completed nearby foods check")
        
    except Exception as e:
        logger.error(f"Error in check_nearby_foods: {str(e)}")

async def check_expiring_foods():
    """
    Check for foods that are about to expire and create notifications.
    
    This task runs periodically to find foods that are about to expire
    and creates notifications for their owners.
    """
    try:
        logger.info("Starting expiring foods check")
        
        # Find foods that expire in the next 24 hours
        tomorrow = datetime.now() + timedelta(days=1)
        
        expiring_foods_query = """
        SELECT f.*, u.first_name, u.last_name
        FROM foods f
        JOIN users u ON f.user_id = u.id
        WHERE f.expiry_date <= %s
        AND f.expiry_date > NOW()
        AND f.is_available = true
        """
        
        expiring_foods_params = [tomorrow.isoformat()]
        
        expiring_foods_result = await execute_raw_sql(expiring_foods_query, expiring_foods_params)
        
        if not expiring_foods_result or "data" not in expiring_foods_result or len(expiring_foods_result["data"]) == 0:
            logger.info("No expiring foods found")
            return
        
        logger.info(f"Found {len(expiring_foods_result['data'])} expiring foods")
        
        # Create notifications for expiring foods
        notifications_created = 0
        
        for food in expiring_foods_result["data"]:
            user_id = food["user_id"]
            
            # Check if notification already exists
            existing_notification = await execute_query(
                table="notifications",
                query_type="select",
                filters={
                    "user_id": user_id,
                    "type": "food_expiring",
                    "related_id": food["id"]
                }
            )
            
            if existing_notification and len(existing_notification) > 0:
                # Notification already exists, skip
                continue
            
            # Create notification
            notification_data = {
                "user_id": user_id,
                "type": "food_expiring",
                "title": "Food Expiring Soon",
                "message": f"Your {food['name']} is expiring soon!",
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
        
        logger.info(f"Created {notifications_created} notifications for expiring foods")
        
    except Exception as e:
        logger.error(f"Error in check_expiring_foods: {str(e)}")

async def run_scheduled_tasks():
    """
    Run all scheduled tasks periodically.
    """
    while True:
        try:
            # Run tasks
            await check_nearby_foods()
            await check_expiring_foods()
            
            # Wait for next run (every hour)
            await asyncio.sleep(3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Error in scheduled tasks: {str(e)}")
            await asyncio.sleep(60)  # Wait a minute before retrying 