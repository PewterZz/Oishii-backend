import os
from typing import Optional, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "SUPABASE_URL and SUPABASE_KEY must be set in environment variables"
    )

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Helper functions for database operations
async def execute_query(
    table: str, 
    query_type: str, 
    data: Optional[Dict[str, Any]] = None, 
    filters: Optional[Dict[str, Any]] = None,
    select: str = "*",
    limit: Optional[int] = None,
    order_by: Optional[Dict[str, str]] = None,
    joins: Optional[list] = None
):
    """
    Execute a query on the Supabase database.
    
    Args:
        table: The table to query
        query_type: The type of query (select, insert, update, delete)
        data: The data to insert or update
        filters: The filters to apply to the query
        select: The columns to select
        limit: The maximum number of rows to return
        order_by: The columns to order by
        joins: The tables to join
        
    Returns:
        The result of the query
    """
    try:
        query = supabase.table(table)
        
        if query_type == "select":
            query = query.select(select)
            
            # Apply joins if provided
            if joins:
                for join in joins:
                    join_table = join.get("table")
                    join_on = join.get("on")
                    join_type = join.get("type", "inner")
                    
                    if join_table and join_on:
                        if join_type == "inner":
                            query = query.join(join_table, join_on)
                        elif join_type == "left":
                            query = query.join(join_table, join_on, join_type="left")
                        elif join_type == "right":
                            query = query.join(join_table, join_on, join_type="right")
                        elif join_type == "full":
                            query = query.join(join_table, join_on, join_type="full")
            
            # Apply filters if provided
            if filters:
                for key, value in filters.items():
                    if isinstance(value, dict):
                        operator = list(value.keys())[0]
                        if operator == "eq":
                            query = query.eq(key, value[operator])
                        elif operator == "neq":
                            query = query.neq(key, value[operator])
                        elif operator == "gt":
                            query = query.gt(key, value[operator])
                        elif operator == "gte":
                            query = query.gte(key, value[operator])
                        elif operator == "lt":
                            query = query.lt(key, value[operator])
                        elif operator == "lte":
                            query = query.lte(key, value[operator])
                        elif operator == "like":
                            query = query.like(key, value[operator])
                        elif operator == "ilike":
                            query = query.ilike(key, value[operator])
                        elif operator == "is":
                            query = query.is_(key, value[operator])
                        elif operator == "in":
                            query = query.in_(key, value[operator])
                        elif operator == "contains":
                            query = query.contains(key, value[operator])
                        elif operator == "containedBy":
                            query = query.contained_by(key, value[operator])
                        elif operator == "rangeGt":
                            query = query.range_gt(key, value[operator])
                        elif operator == "rangeGte":
                            query = query.range_gte(key, value[operator])
                        elif operator == "rangeLt":
                            query = query.range_lt(key, value[operator])
                        elif operator == "rangeLte":
                            query = query.range_lte(key, value[operator])
                        elif operator == "rangeAdjacent":
                            query = query.range_adjacent(key, value[operator])
                        elif operator == "overlaps":
                            query = query.overlaps(key, value[operator])
                        elif operator == "textSearch":
                            query = query.text_search(key, value[operator])
                    else:
                        query = query.eq(key, value)
            
            # Apply order by if provided
            if order_by:
                for key, direction in order_by.items():
                    if direction.lower() == "asc":
                        query = query.order(key, ascending=True)
                    elif direction.lower() == "desc":
                        query = query.order(key, ascending=False)
            
            # Apply limit if provided
            if limit:
                query = query.limit(limit)
            
            result = query.execute()
            return result.data
            
        elif query_type == "insert":
            if not data:
                raise ValueError("Data is required for insert operations")
            
            result = query.insert(data).execute()
            return result.data
            
        elif query_type == "update":
            if not data:
                raise ValueError("Data is required for update operations")
            
            if not filters:
                raise ValueError("Filters are required for update operations")
            
            # Apply filters
            for key, value in filters.items():
                if isinstance(value, dict):
                    operator = list(value.keys())[0]
                    if operator == "eq":
                        query = query.eq(key, value[operator])
                    # Add other operators as needed
                else:
                    query = query.eq(key, value)
            
            result = query.update(data).execute()
            return result.data
            
        elif query_type == "delete":
            if not filters:
                raise ValueError("Filters are required for delete operations")
            
            # Apply filters
            for key, value in filters.items():
                if isinstance(value, dict):
                    operator = list(value.keys())[0]
                    if operator == "eq":
                        query = query.eq(key, value[operator])
                    # Add other operators as needed
                else:
                    query = query.eq(key, value)
            
            result = query.delete().execute()
            return result.data
            
        else:
            raise ValueError(f"Invalid query type: {query_type}")
            
    except Exception as e:
        # Log the error
        print(f"Error executing query: {e}")
        raise e

# Auth functions
async def sign_up(email: str, password: str, user_data: Dict[str, Any]):
    """
    Sign up a new user.
    
    Args:
        email: The user's email
        password: The user's password
        user_data: Additional user data
        
    Returns:
        The new user
    """
    try:
        # Sign up the user with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        # Get the user ID from the auth response
        user_id = auth_response.user.id
   
        user_data["id"] = user_id
        user_data["password"] = password  # Add password to user data
        
        # Insert the user data into the users table
        user_response = await execute_query(
            table="users",
            query_type="insert",
            data=user_data
        )
        
        return user_response[0] if user_response else None
        
    except Exception as e:
        # Log the error
        print(f"Error signing up user: {e}")
        raise e

async def sign_in(email: str, password: str):
    """
    Sign in a user.
    
    Args:
        email: The user's email
        password: The user's password
        
    Returns:
        The user's session
    """
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        return response
        
    except Exception as e:
        # Log the error
        print(f"Error signing in user: {e}")
        raise e

async def sign_out(jwt: str):
    """
    Sign out a user.
    
    Args:
        jwt: The user's JWT
        
    Returns:
        None
    """
    try:
        supabase.auth.sign_out()
        
    except Exception as e:
        # Log the error
        print(f"Error signing out user: {e}")
        raise e

async def get_user(jwt: str):
    """
    Get a user by JWT.
    
    Args:
        jwt: The user's JWT
        
    Returns:
        The user
    """
    try:
        # Set the auth token
        supabase.auth.set_session(jwt)
        
        # Get the user
        user = supabase.auth.get_user()
        
        return user
        
    except Exception as e:
        # Log the error
        print(f"Error getting user: {e}")
        raise e 