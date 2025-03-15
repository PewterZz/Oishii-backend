import os
from typing import Optional, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv
import httpx

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
        # Log the operation for debugging
        print(f"Executing {query_type} on table {table}")
        print(f"Filters: {filters}")
        print(f"Data: {data}")
        
        # Get the base query builder
        query = supabase.table(table)
        
        if query_type == "select":
            # Start with a basic select
            query = query.select(select)
            
            # Execute the query without any filters or options first
            # This is to check if the basic functionality works
            try:
                result = query.execute()
                print("Basic select query executed successfully")
                
                # If we have filters, we need to filter the results manually
                if filters:
                    filtered_data = []
                    for item in result.data:
                        include_item = True
                        for key, value in filters.items():
                            if isinstance(value, dict):
                                # Complex filters not supported in this basic implementation
                                # Just use equality for now
                                operator = list(value.keys())[0]
                                if operator == "eq" and item.get(key) != value[operator]:
                                    include_item = False
                                    break
                            elif item.get(key) != value:
                                include_item = False
                                break
                        if include_item:
                            filtered_data.append(item)
                    
                    # Apply limit if provided
                    if limit and len(filtered_data) > limit:
                        filtered_data = filtered_data[:limit]
                    
                    # Apply order by if provided
                    if order_by:
                        for key, direction in order_by.items():
                            reverse = direction.lower() == "desc"
                            filtered_data.sort(key=lambda x: x.get(key, ""), reverse=reverse)
                    
                    return filtered_data
                else:
                    # Apply limit if provided
                    if limit and len(result.data) > limit:
                        return result.data[:limit]
                    return result.data
                
            except Exception as select_e:
                print(f"Basic select query failed: {select_e}")
                raise select_e
            
        elif query_type == "insert":
            if not data:
                raise ValueError("Data is required for insert operations")
            
            try:
                # Try the standard insert method
                result = query.insert(data).execute()
                print("Insert operation successful")
                return result.data
            except Exception as insert_e:
                print(f"Insert operation failed: {insert_e}")
                
                # Try a direct HTTP request as a last resort
                try:
                    import httpx
                    import json
                    from datetime import datetime
                    
                    # Get the Supabase URL and key from the client
                    supabase_url = SUPABASE_URL
                    supabase_key = SUPABASE_KEY
                    
                    # Construct the URL for the table
                    url = f"{supabase_url}/rest/v1/{table}"
                    
                    # Set up the headers
                    headers = {
                        "apikey": supabase_key,
                        "Authorization": f"Bearer {supabase_key}",
                        "Content-Type": "application/json",
                        "Prefer": "return=representation"
                    }
                    
                    # Serialize the data to handle non-JSON serializable objects
                    serialized_data = {}
                    for key, value in data.items():
                        # Handle different types of values
                        if isinstance(value, datetime):
                            serialized_data[key] = value.isoformat()
                        # Handle URL objects specifically
                        elif str(type(value)).find('Url') != -1 or str(type(value)).find('URL') != -1:
                            serialized_data[key] = str(value)
                        elif hasattr(value, '__dict__'):  # Custom objects
                            serialized_data[key] = str(value)
                        # Handle lists of objects
                        elif isinstance(value, list):
                            serialized_list = []
                            for item in value:
                                if isinstance(item, datetime):
                                    serialized_list.append(item.isoformat())
                                elif str(type(item)).find('Url') != -1 or str(type(item)).find('URL') != -1:
                                    serialized_list.append(str(item))
                                elif hasattr(item, '__dict__'):
                                    serialized_list.append(str(item))
                                else:
                                    serialized_list.append(item)
                            serialized_data[key] = serialized_list
                        else:
                            serialized_data[key] = value
                    
                    # Print the serialized data for debugging
                    print(f"Serialized data: {serialized_data}")
                    
                    # Make the request
                    response = httpx.post(url, json=serialized_data, headers=headers)
                    response.raise_for_status()
                    
                    print("Insert operation successful using direct HTTP request")
                    return response.json()
                except Exception as http_e:
                    print(f"Direct HTTP insert request failed: {http_e}")
                    print(f"Error type: {type(http_e)}")
                    print(f"Error details: {repr(http_e)}")
                    raise http_e
            
        elif query_type == "update":
            if not data:
                raise ValueError("Data is required for update operations")
            
            if not filters:
                raise ValueError("Filters are required for update operations")
            
            try:
                # Try the standard update method
                # We'll need to construct a query string for the filters
                filter_params = []
                for key, value in filters.items():
                    if isinstance(value, dict):
                        # Complex filters not supported in this basic implementation
                        # Just use equality for now
                        operator = list(value.keys())[0]
                        if operator == "eq":
                            filter_params.append(f"{key}=eq.{value[operator]}")
                    else:
                        filter_params.append(f"{key}=eq.{value}")
                
                # Construct the URL for the table with filters
                import httpx
                import json
                from datetime import datetime
                
                # Get the Supabase URL and key from the client
                supabase_url = SUPABASE_URL
                supabase_key = SUPABASE_KEY
                
                # Construct the URL for the table with filters
                url = f"{supabase_url}/rest/v1/{table}?{('&'.join(filter_params))}"
                
                # Set up the headers
                headers = {
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                }
                
                # Serialize the data to handle non-JSON serializable objects
                serialized_data = {}
                for key, value in data.items():
                    # Handle different types of values
                    if isinstance(value, datetime):
                        serialized_data[key] = value.isoformat()
                    # Handle URL objects specifically
                    elif str(type(value)).find('Url') != -1 or str(type(value)).find('URL') != -1:
                        serialized_data[key] = str(value)
                    elif hasattr(value, '__dict__'):  # Custom objects
                        serialized_data[key] = str(value)
                    # Handle lists of objects
                    elif isinstance(value, list):
                        serialized_list = []
                        for item in value:
                            if isinstance(item, datetime):
                                serialized_list.append(item.isoformat())
                            elif str(type(item)).find('Url') != -1 or str(type(item)).find('URL') != -1:
                                serialized_list.append(str(item))
                            elif hasattr(item, '__dict__'):
                                serialized_list.append(str(item))
                            else:
                                serialized_list.append(item)
                        serialized_data[key] = serialized_list
                    else:
                        serialized_data[key] = value
                
                # Print the serialized data for debugging
                print(f"Serialized data: {serialized_data}")
                
                # Make the request
                response = httpx.patch(url, json=serialized_data, headers=headers)
                response.raise_for_status()
                
                print("Update operation successful using direct HTTP request")
                return response.json()
                
            except Exception as update_e:
                print(f"Update operation failed: {update_e}")
                print(f"Error type: {type(update_e)}")
                print(f"Error details: {repr(update_e)}")
                
                # Try one more approach - direct SQL update
                try:
                    print("Attempting direct update through Supabase client...")
                    # Try to use the update method directly
                    result = query.update(data).execute()
                    print("Direct update successful")
                    return result.data
                except Exception as direct_e:
                    print(f"Direct update also failed: {direct_e}")
                    raise update_e
            
        elif query_type == "delete":
            if not filters:
                raise ValueError("Filters are required for delete operations")
            
            try:
                # Try the standard delete method
                # We'll need to construct a query string for the filters
                filter_params = []
                for key, value in filters.items():
                    if isinstance(value, dict):
                        # Complex filters not supported in this basic implementation
                        # Just use equality for now
                        operator = list(value.keys())[0]
                        if operator == "eq":
                            filter_params.append(f"{key}=eq.{value[operator]}")
                    else:
                        filter_params.append(f"{key}=eq.{value}")
                
                # Construct the URL for the table with filters
                import httpx
                
                # Get the Supabase URL and key from the client
                supabase_url = SUPABASE_URL
                supabase_key = SUPABASE_KEY
                
                # Construct the URL for the table with filters
                url = f"{supabase_url}/rest/v1/{table}?{('&'.join(filter_params))}"
                
                # Set up the headers
                headers = {
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                }
                
                # Make the request
                response = httpx.delete(url, headers=headers)
                response.raise_for_status()
                
                print("Delete operation successful using direct HTTP request")
                return response.json()
                
            except Exception as delete_e:
                print(f"Delete operation failed: {delete_e}")
                print(f"Error type: {type(delete_e)}")
                print(f"Error details: {repr(delete_e)}")
                
                # Try one more approach - direct delete
                try:
                    print("Attempting direct delete through Supabase client...")
                    # Try to use the delete method directly
                    for key, value in filters.items():
                        if isinstance(value, dict):
                            # Skip complex filters for now
                            continue
                        query = query.eq(key, value)
                    
                    result = query.delete().execute()
                    print("Direct delete successful")
                    return result.data
                except Exception as direct_e:
                    print(f"Direct delete also failed: {direct_e}")
                    raise delete_e
            
        else:
            raise ValueError(f"Invalid query type: {query_type}")
            
    except Exception as e:
        # Log the error
        print(f"Error executing query: {e}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {repr(e)}")
        print(f"Query type: {query_type}")
        print(f"Table: {table}")
        if filters:
            print(f"Filters: {filters}")
        if data:
            print(f"Data: {data}")
        
        raise e

# Auth functions
async def sign_up(email: str, password: str) -> dict:
    """Sign up a new user with Supabase."""
    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        return response
    except Exception as e:
        print(f"Supabase sign-up error: {str(e)}")
        raise

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

def get_supabase_client() -> Client:
    """Get Supabase client instance."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

async def execute_raw_sql(query: str):
    """
    Execute a raw SQL query using the Supabase REST API.
    
    Args:
        query: The SQL query to execute
        
    Returns:
        The result of the query
    """
    try:
        print(f"Executing raw SQL query: {query}")
        
        # Use the Supabase client to execute the raw SQL query
        result = supabase.rpc("execute_sql", {"query": query}).execute()
        
        print(f"Raw SQL query result: {result}")
        return result
        
    except Exception as e:
        print(f"Error executing raw SQL query: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {repr(e)}")
        
        # Try using the REST API directly
        try:
            import httpx
            
            # Get the Supabase URL and key
            supabase_url = SUPABASE_URL
            supabase_key = SUPABASE_KEY
            
            # Construct the URL for the RPC endpoint
            url = f"{supabase_url}/rest/v1/rpc/execute_sql"
            
            # Set up the headers
            headers = {
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json"
            }
            
            # Make the request
            response = httpx.post(url, json={"query": query}, headers=headers)
            response.raise_for_status()
            
            print(f"Raw SQL query result via REST API: {response.json()}")
            return {"data": response.json()}
            
        except Exception as http_e:
            print(f"REST API approach also failed: {str(http_e)}")
            raise e

async def check_user_exists(user_id: str) -> bool:
    """
    Check if a user exists in Supabase auth.
    
    Args:
        user_id: The user's ID
        
    Returns:
        True if the user exists, False otherwise
    """
    try:
        print(f"Checking if user exists in Supabase auth: {user_id}")
        
        # Try to get the user from Supabase auth
        response = supabase.auth.admin.get_user_by_id(user_id)
        
        # If we get here, the user exists
        print(f"User exists in Supabase auth: {user_id}")
        return True
        
    except Exception as e:
        print(f"Error checking if user exists in Supabase auth: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {repr(e)}")
        
        # Check if the error is related to user not found
        error_str = str(e).lower()
        if "user not found" in error_str or "not found" in error_str:
            print(f"User not found in Supabase auth: {user_id}")
            return False
            
        # For other errors, we're not sure if the user exists or not
        print(f"Unknown error checking if user exists in Supabase auth: {str(e)}")
        return False 