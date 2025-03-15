from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum

class TicketTransactionType(str, Enum):
    EARNED = "earned"       # Earned from sharing a meal
    SPENT = "spent"         # Spent on claiming a meal
    ADMIN = "admin"         # Administrative adjustment
    INITIAL = "initial"     # Initial allocation

class TicketTransaction(BaseModel):
    id: UUID
    user_id: UUID
    amount: int = Field(..., description="Number of tickets (positive for earned, negative for spent)")
    transaction_type: TicketTransactionType
    related_food_id: Optional[UUID] = None
    description: str
    created_at: datetime
    
class TicketBalance(BaseModel):
    user_id: UUID
    balance: int = Field(..., ge=0, description="Current ticket balance")
    last_updated: datetime

class TicketTransactionCreate(BaseModel):
    user_id: UUID
    amount: int
    transaction_type: TicketTransactionType
    related_food_id: Optional[UUID] = None
    description: str 