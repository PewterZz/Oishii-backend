from fastapi import APIRouter
from .endpoints import users, foods, swaps, notifications, ratings

router = APIRouter(prefix="/api/v1")

# Include all routers
router.include_router(users.router, prefix="/users")
router.include_router(foods.router)
router.include_router(swaps.router)
router.include_router(notifications.router)
router.include_router(ratings.router) 