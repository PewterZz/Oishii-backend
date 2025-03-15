from fastapi import APIRouter, HTTPException, status, Depends, Path, Query
from typing import List, Optional
from datetime import datetime
from pydantic import UUID4
from ....schemas.ticket import TicketTransaction, TicketBalance, TicketTransactionCreate, TicketTransactionType
from ...v1.endpoints.users import get_current_user
from ....core.supabase import execute_query

router = APIRouter(prefix="/tickets", tags=["tickets"])

@router.get("/balance", response_model=TicketBalance)
async def get_ticket_balance(current_user: dict = Depends(get_current_user)):
    """
    Get the current user's ticket balance.
    """
    user_id = current_user["id"]
    
    # Check if user has a balance record
    balance = await execute_query(
        table="ticket_balances",
        query_type="select",
        filters={"user_id": user_id}
    )
    
    if not balance or len(balance) == 0:
        # Create initial balance record with 5 tickets
        now = datetime.now().isoformat()
        balance_data = {
            "user_id": user_id,
            "balance": 5,  # Start with 5 tickets
            "last_updated": now
        }
        
        new_balance = await execute_query(
            table="ticket_balances",
            query_type="insert",
            data=balance_data
        )
        
        if not new_balance or len(new_balance) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create ticket balance"
            )
        
        # Create initial transaction record
        transaction_data = {
            "user_id": user_id,
            "amount": 5,
            "transaction_type": TicketTransactionType.INITIAL.value,
            "description": "Initial ticket allocation",
            "created_at": now
        }
        
        await execute_query(
            table="ticket_transactions",
            query_type="insert",
            data=transaction_data
        )
        
        return new_balance[0]
    
    return balance[0]

@router.get("/transactions", response_model=List[TicketTransaction])
async def get_ticket_transactions(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """
    Get the current user's ticket transactions.
    """
    user_id = current_user["id"]
    
    # Get transactions from database
    transactions = await execute_query(
        table="ticket_transactions",
        query_type="select",
        filters={"user_id": user_id},
        order_by={"created_at": "desc"},
        limit=limit
    )
    
    # Skip the first 'skip' transactions
    return transactions[skip:skip + limit]

@router.post("/claim-food/{food_id}", status_code=status.HTTP_200_OK)
async def claim_food(
    food_id: UUID4 = Path(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Claim a food item using tickets.
    """
    user_id = current_user["id"]
    
    # Get food from database
    food = await execute_query(
        table="foods",
        query_type="select",
        filters={"id": str(food_id)}
    )
    
    if not food or len(food) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food not found"
        )
    
    food = food[0]
    
    # Check if food is available
    if not food["is_available"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This food item is not available"
        )
    
    # Check if user is trying to claim their own food
    if food["user_id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot claim your own food"
        )
    
    # Get user's ticket balance
    balance = await execute_query(
        table="ticket_balances",
        query_type="select",
        filters={"user_id": user_id}
    )
    
    if not balance or len(balance) == 0:
        # Create initial balance record
        await get_ticket_balance(current_user)
        
        # Get the newly created balance
        balance = await execute_query(
            table="ticket_balances",
            query_type="select",
            filters={"user_id": user_id}
        )
    
    balance = balance[0]
    
    # Check if user has enough tickets
    tickets_required = food.get("tickets_required", 1)
    if balance["balance"] < tickets_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough tickets. Required: {tickets_required}, Available: {balance['balance']}"
        )
    
    # Update food availability
    await execute_query(
        table="foods",
        query_type="update",
        filters={"id": str(food_id)},
        data={"is_available": False, "updated_at": datetime.now().isoformat()}
    )
    
    # Update user's ticket balance
    new_balance = balance["balance"] - tickets_required
    await execute_query(
        table="ticket_balances",
        query_type="update",
        filters={"user_id": user_id},
        data={"balance": new_balance, "last_updated": datetime.now().isoformat()}
    )
    
    # Create transaction record for spending tickets
    now = datetime.now().isoformat()
    spend_transaction = {
        "user_id": user_id,
        "amount": -tickets_required,
        "transaction_type": TicketTransactionType.SPENT.value,
        "related_food_id": str(food_id),
        "description": f"Claimed food: {food['title']}",
        "created_at": now
    }
    
    await execute_query(
        table="ticket_transactions",
        query_type="insert",
        data=spend_transaction
    )
    
    # Create transaction record for the food provider earning tickets
    earn_transaction = {
        "user_id": food["user_id"],
        "amount": tickets_required,
        "transaction_type": TicketTransactionType.EARNED.value,
        "related_food_id": str(food_id),
        "description": f"Someone claimed your food: {food['title']}",
        "created_at": now
    }
    
    await execute_query(
        table="ticket_transactions",
        query_type="insert",
        data=earn_transaction
    )
    
    # Update provider's ticket balance
    provider_balance = await execute_query(
        table="ticket_balances",
        query_type="select",
        filters={"user_id": food["user_id"]}
    )
    
    if not provider_balance or len(provider_balance) == 0:
        # Create initial balance record for provider
        provider_balance_data = {
            "user_id": food["user_id"],
            "balance": tickets_required,  # Start with earned tickets
            "last_updated": now
        }
        
        await execute_query(
            table="ticket_balances",
            query_type="insert",
            data=provider_balance_data
        )
    else:
        # Update provider's balance
        provider_balance = provider_balance[0]
        new_provider_balance = provider_balance["balance"] + tickets_required
        
        await execute_query(
            table="ticket_balances",
            query_type="update",
            filters={"user_id": food["user_id"]},
            data={"balance": new_provider_balance, "last_updated": now}
        )
    
    # Create a claim record
    claim_data = {
        "food_id": str(food_id),
        "claimer_id": user_id,
        "provider_id": food["user_id"],
        "tickets_spent": tickets_required,
        "status": "claimed",
        "created_at": now,
        "updated_at": now
    }
    
    await execute_query(
        table="food_claims",
        query_type="insert",
        data=claim_data
    )
    
    return {
        "message": f"Successfully claimed food: {food['title']}",
        "tickets_spent": tickets_required,
        "new_balance": new_balance
    } 