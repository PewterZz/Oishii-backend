from fastapi import APIRouter
from .endpoints import users, foods, swaps, notifications, ratings, tickets

router = APIRouter(prefix="/api/v1")

# Include all endpoint routers
router.include_router(users.router, prefix="/users")
router.include_router(foods.router, prefix="/foods")
router.include_router(swaps.router, prefix="/swaps")
router.include_router(notifications.router, prefix="/notifications")
router.include_router(ratings.router, prefix="/ratings")
router.include_router(tickets.router, prefix="/tickets") 