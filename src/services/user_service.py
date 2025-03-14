from schemas.user import UserCreate, UserUpdate
from core.exceptions import NotFoundError
from typing import List, Dict

class UserService:
    def __init__(self):
        self.users: List[Dict] = []

    async def create_user(self, user: UserCreate) -> Dict:
        new_user = {
            **user.model_dump(),
            "id": len(self.users) + 1
        }
        self.users.append(new_user)
        return new_user

    async def get_users(self) -> List[Dict]:
        return self.users

    async def get_user_by_id(self, user_id: int) -> Dict:
        user = next((user for user in self.users if user["id"] == user_id), None)
        if not user:
            raise NotFoundError(detail="User not found")
        return user

    async def update_user(self, user_id: int, user_update: UserUpdate) -> Dict:
        user_idx = next((idx for idx, user in enumerate(self.users) 
                        if user["id"] == user_id), None)
        if user_idx is None:
            raise NotFoundError(detail="User not found")
        
        update_data = user_update.model_dump(exclude_unset=True)
        self.users[user_idx].update(update_data)
        return self.users[user_idx] 