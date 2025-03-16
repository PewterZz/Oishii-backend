import os
import json
import logging
import requests
import time
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables if not already loaded
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Loaded environment variables from .env file")
except ImportError:
    logger.warning("dotenv package not available, skipping .env loading")

# DataStax Langflow configuration
BASE_API_URL = os.getenv("DATASTAX_LANGFLOW_API_URL", "https://api.langflow.astra.datastax.com")
LANGFLOW_ID = os.getenv("DATASTAX_LANGFLOW_ID", "f97d1e16-3dd8-4355-99fa-e8f1b98563ae")
FLOW_ID = os.getenv("DATASTAX_FLOW_ID", "567ad106-a9f3-4e30-b909-628e89186549")

# Fix token by removing any line breaks or whitespace
raw_token = os.getenv("DATASTAX_APPLICATION_TOKEN", "")
APPLICATION_TOKEN = "".join(raw_token.split()) if raw_token else ""
logger.info(f"Fixed APPLICATION_TOKEN. Original length: {len(raw_token)}, New length: {len(APPLICATION_TOKEN)}")

ENDPOINT = os.getenv("DATASTAX_ENDPOINT", "")  # You can set a specific endpoint name in the flow settings

# Fix refresh token by removing any line breaks or whitespace
raw_refresh_token = os.getenv("DATASTAX_REFRESH_TOKEN", "")
REFRESH_TOKEN = "".join(raw_refresh_token.split()) if raw_refresh_token else ""
logger.info(f"Fixed REFRESH_TOKEN. Original length: {len(raw_refresh_token)}, New length: {len(REFRESH_TOKEN)}")

TOKEN_EXPIRY = 0  # Track token expiry time

# Debug token loading
logger.info(f"DataStax token configuration:")
logger.info(f"  Application token available: {'Yes' if APPLICATION_TOKEN else 'No'}")
logger.info(f"  Application token length: {len(APPLICATION_TOKEN) if APPLICATION_TOKEN else 0}")
logger.info(f"  Refresh token available: {'Yes' if REFRESH_TOKEN else 'No'}")
logger.info(f"  Refresh token length: {len(REFRESH_TOKEN) if REFRESH_TOKEN else 0}")

# Check if refresh token is the same as application token (common mistake)
if REFRESH_TOKEN == APPLICATION_TOKEN:
    logger.warning("DATASTAX_REFRESH_TOKEN is the same as DATASTAX_APPLICATION_TOKEN. This may not work for token refresh.")
    # For DataStax, sometimes the same token can be used for both auth and refresh
    # We'll keep it as is and let the API determine if it works

# Default tweaks - can be customized per request
DEFAULT_TWEAKS = {
    "Agent-2vwsZ": {},
    "ChatInput-5yMvY": {},
    "ChatOutput-5gdX7": {},
    "URL-Avwp7": {},
    "CalculatorComponent-Hh47N": {}
}

# Optional: Import langflow if available for file upload functionality
try:
    from langflow.load import upload_file
    HAS_LANGFLOW = True
except ImportError:
    logger.warning("Langflow package is not available for file upload functionality")
    HAS_LANGFLOW = False
    upload_file = None


async def refresh_auth_token() -> str:
    """
    Refresh the DataStax authentication token when it expires.
    
    Returns:
        A new valid authentication token
    """
    global APPLICATION_TOKEN, TOKEN_EXPIRY, REFRESH_TOKEN
    
    logger.info("Refreshing DataStax authentication token...")
    
    # Try to reload refresh token if not available
    if not REFRESH_TOKEN:
        REFRESH_TOKEN = os.getenv("DATASTAX_REFRESH_TOKEN", "")
        logger.info(f"Reloaded REFRESH_TOKEN from environment. Length: {len(REFRESH_TOKEN) if REFRESH_TOKEN else 0}")
    
    # Check if we have a refresh token
    if not REFRESH_TOKEN:
        logger.error("No refresh token available. Cannot refresh authentication token.")
        return APPLICATION_TOKEN
    
    # Check if refresh token is the same as application token
    if REFRESH_TOKEN == APPLICATION_TOKEN:
        logger.warning("Refresh token is identical to application token. This may cause refresh issues.")
        # Try to use it anyway, as some APIs allow using the same token
    
    try:
        # Validate current token first
        logger.info("Validating current DataStax token...")
        validation_url = f"{BASE_API_URL}/lf/{LANGFLOW_ID}/api/v1/validate"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {APPLICATION_TOKEN}"
        }
        
        try:
            validation_response = requests.get(validation_url, headers=headers, timeout=10)
            
            # If the token is valid, just use it
            if validation_response.status_code == 200:
                logger.info("Current token is still valid. No need to refresh.")
                TOKEN_EXPIRY = time.time() + 3600  # Set expiry to 1 hour from now
                return APPLICATION_TOKEN
        except requests.exceptions.RequestException as e:
            logger.warning(f"Token validation request failed: {e}")
        
        # Current token is invalid. Attempting to use refresh token...
        logger.info("Current token is invalid. Attempting to use refresh token...")
        
        # For DataStax, try different refresh approaches
        refresh_approaches = [
            # Approach 1: Standard OAuth refresh
            {
                "url": f"{BASE_API_URL}/auth/refresh",
                "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {REFRESH_TOKEN}"},
                "payload": {"refresh_token": REFRESH_TOKEN}
            },
            # Approach 2: DataStax specific refresh
            {
                "url": f"{BASE_API_URL}/api/token/refresh",
                "headers": {"Content-Type": "application/json"},
                "payload": {"token": REFRESH_TOKEN}
            },
            # Approach 3: Try using the refresh token as the application token
            {
                "url": validation_url,
                "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {REFRESH_TOKEN}"},
                "payload": {}
            }
        ]
        
        # Try each approach
        for i, approach in enumerate(refresh_approaches):
            try:
                logger.info(f"Trying token refresh approach {i+1}...")
                
                # Use POST for refresh, GET for validation
                if "refresh" in approach["url"]:
                    response = requests.post(
                        approach["url"], 
                        headers=approach["headers"], 
                        json=approach["payload"],
                        timeout=10
                    )
                else:
                    response = requests.get(
                        approach["url"], 
                        headers=approach["headers"],
                        timeout=10
                    )
                
                # Check for CloudFront errors (which return HTML)
                if response.status_code == 403 and "<!DOCTYPE HTML" in response.text:
                    logger.warning(f"Approach {i+1} failed with CloudFront 403 error. This may indicate IP restrictions or rate limiting.")
                    continue
                
                if response.status_code == 200:
                    # For validation approach, just use the refresh token as the application token
                    if "validate" in approach["url"]:
                        logger.info("Refresh token is valid as an application token. Using it directly.")
                        APPLICATION_TOKEN = REFRESH_TOKEN
                        TOKEN_EXPIRY = time.time() + 3600  # 1 hour
                        return APPLICATION_TOKEN
                    
                    # For refresh approaches, extract the new token
                    try:
                        token_data = response.json()
                        logger.info(f"Token refresh response keys: {token_data.keys()}")
                        
                        # Different APIs might use different field names
                        new_token = token_data.get("access_token") or token_data.get("token") or token_data.get("accessToken")
                        expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour if not specified
                        
                        if new_token:
                            APPLICATION_TOKEN = new_token
                            TOKEN_EXPIRY = time.time() + expires_in - 300  # Set expiry with 5-minute buffer
                            logger.info(f"Successfully refreshed authentication token. Valid for {expires_in} seconds.")
                            return new_token
                        else:
                            logger.warning("Token refresh response did not contain a new token.")
                    except Exception as e:
                        logger.warning(f"Error parsing token refresh response: {e}")
                else:
                    logger.warning(f"Approach {i+1} failed with status code: {response.status_code}")
                    # Log response content for debugging, but avoid logging large HTML responses
                    if response.headers.get('content-type') and 'application/json' in response.headers.get('content-type'):
                        try:
                            error_data = response.json()
                            logger.warning(f"Response: {json.dumps(error_data)[:100]}...")
                        except:
                            logger.warning(f"Response: {response.text[:100]}...")
            except Exception as e:
                logger.warning(f"Error with refresh approach {i+1}: {e}")
        
        # If we get here, all approaches failed
        logger.error("All token refresh approaches failed.")
        
        # As a last resort, try to get a new token from the environment
        try:
            logger.info("Attempting to reload token from environment as last resort...")
            new_app_token = os.getenv("DATASTAX_APPLICATION_TOKEN", "")
            new_app_token = "".join(new_app_token.split()) if new_app_token else ""
            
            if new_app_token and new_app_token != APPLICATION_TOKEN:
                logger.info("Found a different token in the environment. Using it.")
                APPLICATION_TOKEN = new_app_token
                TOKEN_EXPIRY = time.time() + 1800  # Set a shorter expiry (30 min) for this fallback
                return APPLICATION_TOKEN
        except Exception as e:
            logger.error(f"Error reloading token from environment: {e}")
    
    except Exception as e:
        logger.error(f"Error refreshing authentication token: {e}")
    
    # If all refresh attempts failed, return the original token
    logger.warning("Token refresh failed. Using the existing application token.")
    # Set a short expiry to try again soon
    TOKEN_EXPIRY = time.time() + 300  # 5 minutes
    return APPLICATION_TOKEN


async def get_valid_token() -> str:
    """
    Get a valid authentication token, refreshing if necessary.
    
    Returns:
        A valid authentication token
    """
    global TOKEN_EXPIRY, APPLICATION_TOKEN
    
    # Debug token state
    logger.info(f"get_valid_token called. Current token state:")
    logger.info(f"  APPLICATION_TOKEN length: {len(APPLICATION_TOKEN) if APPLICATION_TOKEN else 0}")
    logger.info(f"  TOKEN_EXPIRY: {TOKEN_EXPIRY}")
    logger.info(f"  Current time: {time.time()}")
    
    # If no token is available, try to reload from environment
    if not APPLICATION_TOKEN:
        APPLICATION_TOKEN = os.getenv("DATASTAX_APPLICATION_TOKEN", "")
        APPLICATION_TOKEN = "".join(APPLICATION_TOKEN.split()) if APPLICATION_TOKEN else ""
        logger.info(f"Reloaded APPLICATION_TOKEN from environment. Length: {len(APPLICATION_TOKEN) if APPLICATION_TOKEN else 0}")
    
    if not REFRESH_TOKEN and not APPLICATION_TOKEN:
        logger.warning("No application token or refresh token available after reload attempt.")
        return ""
    
    # Check if token is expired or about to expire
    current_time = time.time()
    if current_time > TOKEN_EXPIRY:
        logger.info(f"Token expired or about to expire. Current time: {current_time}, Expiry: {TOKEN_EXPIRY}")
        
        # Try to validate the current token before refreshing
        validation_url = f"{BASE_API_URL}/lf/{LANGFLOW_ID}/api/v1/validate"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {APPLICATION_TOKEN}"
        }
        
        try:
            # Try a quick validation request
            validation_response = requests.get(validation_url, headers=headers, timeout=5)
            
            # If the token is still valid, update the expiry and return it
            if validation_response.status_code == 200:
                logger.info("Current token is still valid despite expiry time. Updating expiry.")
                TOKEN_EXPIRY = current_time + 3600  # Set expiry to 1 hour from now
                return APPLICATION_TOKEN
        except Exception as e:
            logger.warning(f"Token validation check failed: {e}")
        
        # If validation failed or we couldn't check, try to refresh
        refreshed_token = await refresh_auth_token()
        
        # If refresh failed and we still have an application token, use it
        if not refreshed_token and APPLICATION_TOKEN:
            logger.warning("Token refresh failed but we have an application token. Using it as fallback.")
            # Set a short expiry to try refreshing again soon
            TOKEN_EXPIRY = current_time + 300  # 5 minutes
            return APPLICATION_TOKEN
            
        return refreshed_token
    
    logger.info(f"Using existing valid token. Expires in {TOKEN_EXPIRY - current_time} seconds.")
    return APPLICATION_TOKEN


async def run_langflow(
    message: str,
    endpoint: Optional[str] = None,
    output_type: str = "text",
    input_type: str = "text",
    tweaks: Optional[Dict[str, Any]] = None,
    application_token: Optional[str] = None,
    file_path: Optional[str] = None,
    components: Optional[List[str]] = None,
    retry_on_auth_error: bool = True
) -> Dict[str, Any]:
    """
    Run a message through the DataStax Langflow API.
    
    Args:
        message: The message to process
        endpoint: The endpoint ID to use (defaults to FLOW_ID)
        output_type: The output type (text, chat, any, debug)
        input_type: The input type (text, chat, any)
        tweaks: Optional tweaks to apply to the flow
        application_token: Optional application token (if not provided, will use get_valid_token)
        file_path: Optional file path to upload
        components: Optional list of components to include in the response
        retry_on_auth_error: Whether to retry on authentication errors
        
    Returns:
        The response from the API
    """
    # Validate input_type and output_type
    valid_input_types = ["text", "chat", "any"]
    valid_output_types = ["text", "chat", "any", "debug"]
    
    if input_type not in valid_input_types:
        logger.warning(f"Invalid input_type: {input_type}. Must be one of {valid_input_types}. Using 'text' instead.")
        input_type = "text"
    
    if output_type not in valid_output_types:
        logger.warning(f"Invalid output_type: {output_type}. Must be one of {valid_output_types}. Using 'text' instead.")
        output_type = "text"
    
    # Get a valid token if not provided
    if not application_token:
        application_token = await get_valid_token()
    
    # Use the provided endpoint or fall back to FLOW_ID
    endpoint = endpoint or FLOW_ID or ENDPOINT
    
    # If no endpoint is available, return an error
    if not endpoint:
        return {
            "error": True,
            "message": "No endpoint or flow ID configured",
            "status_code": 400
        }
    
    # Construct the API URL
    api_url = f"{BASE_API_URL}/lf/{LANGFLOW_ID}/api/v1/run/{endpoint}"
    
    # Debug configuration
    logger.info(f"DataStax Langflow Configuration:")
    logger.info(f"  API URL: {BASE_API_URL}")
    logger.info(f"  Langflow ID: {LANGFLOW_ID}")
    logger.info(f"  Endpoint/Flow ID: {endpoint}")
    logger.info(f"  Full API URL: {api_url}")
    logger.info(f"  Token provided: {'Yes' if application_token else 'No'}")
    logger.info(f"  Token length: {len(application_token) if application_token else 0}")
    logger.info(f"  Input type: {input_type}")
    logger.info(f"  Output type: {output_type}")

    # Prepare payload
    payload = {
        "input_value": message,
        "output_type": output_type,
        "input_type": input_type,
    }
    
    # Add tweaks if provided
    if tweaks:
        payload["tweaks"] = tweaks
    
    # Prepare headers
    headers = {
        "Content-Type": "application/json"
    }
    
    if application_token:
        headers["Authorization"] = f"Bearer {application_token}"
    
    try:
        # Make the API request
        logger.info(f"Calling DataStax Langflow API at {api_url}")
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        # Check for authentication errors
        if response.status_code == 401 and retry_on_auth_error:
            error_data = {}
            try:
                error_data = response.json()
            except:
                pass
                
            # Check if token expired
            if "expired" in response.text.lower() or "Invalid authentication token" in response.text:
                logger.warning("Authentication token expired. Refreshing token and retrying...")
                # Refresh token and retry
                new_token = await refresh_auth_token()
                return await run_langflow(
                    message=message,
                    endpoint=endpoint,
                    output_type=output_type,
                    input_type=input_type,
                    tweaks=tweaks,
                    application_token=new_token,
                    file_path=file_path,
                    components=components,
                    retry_on_auth_error=False  # Prevent infinite retry loop
                )
        
        # Check for validation errors
        if response.status_code == 422:
            try:
                error_data = response.json()
                logger.error(f"Error response data: {error_data}")
                
                # Check if the error is related to input_type or output_type
                if "input_type" in str(error_data) or "output_type" in str(error_data):
                    logger.warning("Validation error with input_type or output_type. Retrying with default values.")
                    return await run_langflow(
                        message=message,
                        endpoint=endpoint,
                        output_type="text",  # Use default
                        input_type="text",   # Use default
                        tweaks=tweaks,
                        application_token=application_token,
                        file_path=file_path,
                        components=components,
                        retry_on_auth_error=retry_on_auth_error
                    )
            except Exception as e:
                logger.error(f"Error parsing validation error response: {e}")
        
        # Process the response
        try:
            if response.status_code == 200:
                return response.json()
            else:
                # Try to parse error response
                try:
                    error_data = response.json()
                    error_message = f"DataStax Langflow API returned status code {response.status_code}: {error_data}"
                except Exception:
                    # If we can't parse JSON, use the text response
                    error_message = f"DataStax Langflow API returned status code {response.status_code}: {response.text[:200]}"
                
                logger.error(error_message)
                return {
                    "error": True,
                    "message": error_message,
                    "status_code": response.status_code
                }
        except Exception as e:
            logger.error(f"Error processing API response: {e}")
            return {
                "error": True,
                "message": f"Error processing API response: {str(e)}",
                "status_code": response.status_code if 'response' in locals() else 500
            }
    except Exception as e:
        logger.error(f"Error calling DataStax Langflow API: {e}")
        return {
            "error": True,
            "message": f"Error calling DataStax Langflow API: {str(e)}",
            "status_code": 500
        }


async def get_ai_food_recommendations(
    query: str,
    user_preferences: Optional[Dict[str, Any]] = None,
    limit: int = 5,
    file_path: Optional[str] = None,
    application_token: Optional[str] = None,
    available_foods: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Get AI-powered food recommendations using DataStax Langflow.
    
    Args:
        query: The user's food query or request
        user_preferences: Optional user preferences to customize recommendations
        limit: Maximum number of recommendations to return
        file_path: Optional path to a file (e.g., image of food) to analyze
        application_token: Optional application token for authentication (defaults to env variable)
        available_foods: Optional list of available foods in the database to constrain recommendations
        
    Returns:
        Dictionary containing AI recommendations and metadata
    """
    # Log the function call
    logger.info(f"get_ai_food_recommendations called with query: '{query[:100]}...'")
    logger.info(f"User preferences provided: {user_preferences is not None}")
    logger.info(f"Available foods provided: {available_foods is not None}")
    
    # Get a valid token if not provided
    if application_token is None:
        application_token = await get_valid_token()
    
    # Check if token is available
    if not application_token:
        error_msg = "DataStax Langflow application token is missing or invalid"
        logger.error(error_msg)
        return {
            "success": False,
            "query": query,
            "recommendations": [],
            "user_preferences_applied": user_preferences is not None,
            "error": error_msg
        }
    
    # Prepare the message with user preferences and available foods
    message = {
        "query": query,
        "limit": limit
    }
    
    # Add user preferences if provided
    if user_preferences:
        message["user_preferences"] = user_preferences
        
    # Add available foods if provided
    if available_foods:
        message["available_foods"] = available_foods[:50]  # Limit to 50 foods to avoid token limits
    
    # Convert message to JSON string
    message_str = json.dumps(message)
    
    try:
        # Call the DataStax Langflow API
        response = await run_langflow(
            message=message_str,
            application_token=application_token,
            output_type="text",  # Use text output type
            input_type="text"    # Use text input type
        )
        
        # Check for errors
        if response.get("error"):
            logger.error(f"Error from DataStax Langflow API: {response.get('message')}")
            return {
                "success": False,
                "query": query,
                "recommendations": [],
                "user_preferences_applied": user_preferences is not None,
                "error": response.get("message")
            }
        
        # Process the response
        try:
            # Extract recommendations from the response
            recommendations = process_ai_recommendations(response, limit)
            
            return {
                "success": True,
                "query": query,
                "recommendations": recommendations,
                "user_preferences_applied": user_preferences is not None,
                "available_foods_used": available_foods is not None
            }
        except Exception as e:
            logger.error(f"Error processing AI recommendations: {e}")
            logger.info(f"Raw response from langflow service: {json.dumps(response)[:500]}...")
            return {
                "success": False,
                "query": query,
                "recommendations": [],
                "user_preferences_applied": user_preferences is not None,
                "error": f"Error processing AI recommendations: {str(e)}"
            }
    except Exception as e:
        logger.error(f"Error calling DataStax Langflow API: {e}")
        return {
            "success": False,
            "query": query,
            "recommendations": [],
            "user_preferences_applied": user_preferences is not None,
            "error": f"Error calling DataStax Langflow API: {str(e)}"
        }


def process_ai_recommendations(response: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    """
    Process the raw AI response into structured food recommendations.
    
    Args:
        response: Raw response from the Langflow API
        limit: Maximum number of recommendations to return
        
    Returns:
        List of structured food recommendations
    """
    recommendations = []
    
    # Log the response structure for debugging
    logger.info(f"Processing response structure: {type(response)}")
    if isinstance(response, dict):
        logger.info(f"Response keys: {list(response.keys())}")
    
    try:
        # Extract recommendations from the response
        # Handle the specific structure from DataStax Langflow
        if isinstance(response, dict):
            # Check for the outputs structure from DataStax Langflow
            if "outputs" in response:
                outputs = response.get("outputs", [])
                if outputs and isinstance(outputs, list):
                    for output in outputs:
                        # Navigate through the nested structure
                        if "outputs" in output and isinstance(output["outputs"], list):
                            for inner_output in output["outputs"]:
                                if "results" in inner_output and isinstance(inner_output["results"], dict):
                                    results = inner_output["results"]
                                    
                                    # Check for message structure
                                    if "message" in results and isinstance(results["message"], dict):
                                        message = results["message"]
                                        
                                        # Extract text content
                                        if "data" in message and isinstance(message["data"], dict):
                                            data = message["data"]
                                            
                                            # Check for text content
                                            text_key = message.get("text_key", "text")
                                            text_content = data.get(text_key, "")
                                            
                                            if text_content:
                                                # Try to parse as JSON first
                                                try:
                                                    json_data = json.loads(text_content)
                                                    if isinstance(json_data, list):
                                                        # If it's a list, assume it's a list of recommendations
                                                        recommendations = json_data
                                                    elif isinstance(json_data, dict):
                                                        # If it's a dict, check if it has a recommendations key
                                                        if "recommendations" in json_data:
                                                            recommendations = json_data["recommendations"]
                                                        else:
                                                            # Treat the dict as a single recommendation
                                                            recommendations = [json_data]
                                                except json.JSONDecodeError:
                                                    # If it's not valid JSON, try to parse as text
                                                    try:
                                                        # Split by numbered items (1., 2., etc.)
                                                        import re
                                                        rec_texts = re.split(r'\n\d+\.|\n\n', text_content)
                                                        
                                                        # Process each recommendation text
                                                        for i, rec_text in enumerate(rec_texts):
                                                            if not rec_text.strip():
                                                                continue
                                                                
                                                            # Extract name and description
                                                            lines = rec_text.strip().split('\n')
                                                            if lines:
                                                                name = lines[0].strip()
                                                                description = ' '.join(lines[1:]) if len(lines) > 1 else ""
                                                                
                                                                recommendations.append({
                                                                    "name": name,
                                                                    "description": description,
                                                                    "ingredients": None,
                                                                    "preparation": None,
                                                                    "nutritional_info": None,
                                                                    "cuisine_type": None,
                                                                    "dietary_tags": None,
                                                                    "confidence_score": None
                                                                })
                                                    except Exception as e:
                                                        logger.warning(f"Error parsing text as recommendations: {e}")
                                                        # Fallback: treat the entire text as a single recommendation
                                                        recommendations = [{
                                                            "name": "AI Food Recommendation",
                                                            "description": text_content,
                                                            "ingredients": None,
                                                            "preparation": None,
                                                            "nutritional_info": None,
                                                            "cuisine_type": None,
                                                            "dietary_tags": None,
                                                            "confidence_score": None
                                                        }]
            
            # If we still don't have recommendations, try other approaches
            if not recommendations:
                # Try the original approach with result key
                result = response.get("result", "")
                
                if isinstance(result, str):
                    # If result is a string, try to parse it as JSON
                    try:
                        json_data = json.loads(result)
                        if isinstance(json_data, list):
                            recommendations = json_data
                        elif isinstance(json_data, dict) and "recommendations" in json_data:
                            recommendations = json_data["recommendations"]
                    except json.JSONDecodeError:
                        # If it's not valid JSON, use it as a single recommendation
                        recommendations = [{
                            "name": "AI Food Recommendation",
                            "description": result,
                            "ingredients": None,
                            "preparation": None,
                            "nutritional_info": None,
                            "cuisine_type": None,
                            "dietary_tags": None,
                            "confidence_score": None
                        }]
                elif isinstance(result, dict):
                    # If result is a dict, check if it has recommendations
                    if "recommendations" in result:
                        recommendations = result["recommendations"]
                    else:
                        # Use the dict as a single recommendation
                        recommendations = [result]
                elif isinstance(result, list):
                    # If result is already a list, use it directly
                    recommendations = result
    except Exception as e:
        logger.error(f"Error processing AI response: {e}")
        # Return empty list on error
        return []
    
    # Ensure recommendations are properly structured
    structured_recommendations = []
    for i, rec in enumerate(recommendations[:limit]):
        if isinstance(rec, str):
            # If it's a string, use it as the name/description
            structured_recommendations.append({
                "name": f"Recommendation {i+1}",
                "description": rec,
                "ingredients": None,
                "preparation": None,
                "nutritional_info": None,
                "cuisine_type": None,
                "dietary_tags": None,
                "confidence_score": None
            })
        elif isinstance(rec, dict):
            # If it's already a dictionary, ensure it has all expected fields
            structured_recommendations.append({
                "name": rec.get("name", f"Recommendation {i+1}"),
                "description": rec.get("description"),
                "ingredients": rec.get("ingredients"),
                "preparation": rec.get("preparation"),
                "nutritional_info": rec.get("nutritional_info"),
                "cuisine_type": rec.get("cuisine_type"),
                "dietary_tags": rec.get("dietary_tags"),
                "confidence_score": rec.get("confidence_score")
            })
    
    # Log the extracted recommendations
    logger.info(f"Extracted {len(structured_recommendations)} recommendations")
    
    return structured_recommendations 