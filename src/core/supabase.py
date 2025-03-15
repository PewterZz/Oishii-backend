import os
from typing import Optional, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_URL = os.getenv("API_URL", "http://localhost:8000")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "SUPABASE_URL and SUPABASE_KEY must be set in environment variables"
    )

# Create Supabase client with default settings
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Print Supabase configuration for debugging
print(f"Supabase URL: {SUPABASE_URL}")
print(f"API URL: {API_URL}")
print(f"Callback URL: {API_URL}/api/v1/users/callback")

# Helper function to verify tokens
async def verify_token(token: str, type: str = "signup") -> Dict[str, Any]:
    """
    Verify a token with Supabase.
    
    Args:
        token: The token to verify
        type: The type of verification (signup, recovery, invite)
        
    Returns:
        The verification response
    """
    try:
        print(f"Verifying token of type {type}")
        print(f"Token: {token[:10]}... (truncated)")
        
        verify_params = {
            "token": token,
            "type": type
        }
        
        response = supabase.auth.verify_otp(verify_params)
        print(f"Verification response type: {type(response)}")
        print(f"Verification response attributes: {dir(response)}")
        
        return response
    except Exception as e:
        print(f"Error verifying token: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {repr(e)}")
        raise e

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
async def sign_up(email: str, password: str, user_data: Dict[str, Any], redirect_url: Optional[str] = None):
    """
    Sign up a new user.
    
    Args:
        email: The user's email
        password: The user's password
        user_data: Additional user data
        redirect_url: URL to redirect to after email confirmation
        
    Returns:
        The new user
    """
    try:
        # Ensure we have a redirect URL for email confirmation
        if not redirect_url:
            api_url = os.getenv("API_URL", "http://localhost:8000").rstrip('/')
            redirect_url = f"{api_url}/api/v1/users/callback"
        
        # Make sure the redirect URL doesn't have a trailing slash
        redirect_url = redirect_url.rstrip('/')
            
        print(f"Signing up user with redirect URL: {redirect_url}")
        
        # Sign up the user with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": user_data,
                "email_redirect_to": redirect_url,
                # We don't need to add additional email template data
                # Supabase will automatically include the necessary parameters
            }
        })
        
        print(f"Auth response type: {type(auth_response)}")
        print(f"Auth response dir: {dir(auth_response)}")
        print(f"Auth response dict: {auth_response.__dict__}")
        
        # Get the user data from the auth response
        user = auth_response.user
        print(f"User type: {type(user)}")
        print(f"User dir: {dir(user)}")
        print(f"User dict: {user.__dict__}")
        
        if not user:
            print("Could not extract user data from auth response")
            raise ValueError("Failed to create user in Supabase Auth")
        
        # Convert user data to dictionary
        user_dict = {
            "id": user.id,
            "email": user.email,
            "is_verified": False
        }
        
        print(f"Created user dict: {user_dict}")
        
        return user_dict
        
    except Exception as e:
        # Log the error
        print(f"Error signing up user: {e}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {repr(e)}")
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
        print(f"Signing in user with email: {email}")
        
        # Sign in with password
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        print(f"Sign-in response type: {type(response)}")
        print(f"Sign-in response attributes: {dir(response)}")
        
        return response
        
    except Exception as e:
        # Log the error
        print(f"Error signing in user: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {repr(e)}")
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