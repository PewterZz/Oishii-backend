from fastapi import APIRouter, HTTPException, status
from typing import List
from ....schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

# In-memory storage for demo purposes
users_db = []

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    new_user = {**user.model_dump(), "id": len(users_db) + 1}
    users_db.append(new_user)
    return new_user

@router.get("/", response_model=List[UserResponse])
async def get_users():
    return users_db

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    user = next((user for user in users_db if user["id"] == user_id), None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: UserUpdate):
    user_idx = next((idx for idx, user in enumerate(users_db) 
                     if user["id"] == user_id), None)
    if user_idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    update_data = user_update.model_dump(exclude_unset=True)
    users_db[user_idx].update(update_data)
    return users_db[user_idx] 