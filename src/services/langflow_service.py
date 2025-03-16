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
    
    # Try to reload refresh token if not available
    if not REFRESH_TOKEN:
        REFRESH_TOKEN = os.getenv("DATASTAX_REFRESH_TOKEN", "")
        logger.info(f"Reloaded REFRESH_TOKEN from environment. Length: {len(REFRESH_TOKEN) if REFRESH_TOKEN else 0}")
    
    # Check if we have a refresh token
    if not REFRESH_TOKEN:
        logger.error("No refresh token available. Cannot refresh authentication token.")
        return APPLICATION_TOKEN
    
    try:
        # Call the DataStax token refresh endpoint
        refresh_url = f"{BASE_API_URL}/auth/refresh"
        
        # DataStax may use different refresh mechanisms depending on the token type
        # Try the standard Bearer token approach first
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {REFRESH_TOKEN}"
        }
        
        logger.info("Refreshing DataStax authentication token...")
        logger.info(f"Using refresh URL: {refresh_url}")
        
        # Some DataStax APIs expect the token in the request body instead of headers
        payload = {
            "refresh_token": REFRESH_TOKEN
        }
        
        # Try with both header and body approaches
        response = requests.post(refresh_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            token_data = response.json()
            logger.info(f"Token refresh response: {token_data.keys()}")
            
            # Different APIs might use different field names
            new_token = token_data.get("access_token") or token_data.get("token") or token_data.get("accessToken")
            expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour if not specified
            
            if new_token:
                APPLICATION_TOKEN = new_token
                TOKEN_EXPIRY = time.time() + expires_in - 300  # Set expiry with 5-minute buffer
                logger.info(f"Successfully refreshed authentication token. Valid for {expires_in} seconds.")
                return new_token
            else:
                logger.error("Token refresh response did not contain a new token.")
                logger.error(f"Response content: {token_data}")
        else:
            logger.error(f"Failed to refresh token. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            
            # If the standard approach failed, try an alternative approach
            # Some DataStax services use a different endpoint or mechanism
            if response.status_code == 401:
                logger.info("Trying alternative token refresh approach...")
                alt_refresh_url = f"{BASE_API_URL}/api/token/refresh"
                alt_response = requests.post(alt_refresh_url, json={"token": REFRESH_TOKEN})
                
                if alt_response.status_code == 200:
                    alt_token_data = alt_response.json()
                    new_token = alt_token_data.get("access_token") or alt_token_data.get("token")
                    
                    if new_token:
                        APPLICATION_TOKEN = new_token
                        TOKEN_EXPIRY = time.time() + 3600 - 300  # Default 1 hour with 5-min buffer
                        logger.info("Successfully refreshed token using alternative approach.")
                        return new_token
                    else:
                        logger.error("Alternative token refresh did not return a new token.")
                else:
                    logger.error(f"Alternative token refresh failed. Status: {alt_response.status_code}")
    
    except Exception as e:
        logger.error(f"Error refreshing authentication token: {e}")
    
    # If all refresh attempts failed, return the original token
    logger.warning("Token refresh failed. Using the existing application token.")
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
        logger.info(f"Reloaded APPLICATION_TOKEN from environment. Length: {len(APPLICATION_TOKEN) if APPLICATION_TOKEN else 0}")
    
    if not REFRESH_TOKEN and not APPLICATION_TOKEN:
        logger.warning("No application token or refresh token available after reload attempt.")
        return ""
    
    # Check if token is expired or about to expire
    current_time = time.time()
    if current_time > TOKEN_EXPIRY:
        logger.info(f"Token expired or about to expire. Current time: {current_time}, Expiry: {TOKEN_EXPIRY}")
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
    output_type: str = "chat",
    input_type: str = "chat",
    tweaks: Optional[Dict[str, Any]] = None,
    application_token: Optional[str] = None,
    file_path: Optional[str] = None,
    components: Optional[List[str]] = None,
    retry_on_auth_error: bool = True
) -> Dict[str, Any]:
    """
    Run a DataStax Langflow with a given message and optional tweaks.

    Args:
        message: The message to send to the flow
        endpoint: The ID or the endpoint name of the flow (defaults to env variable)
        output_type: The output type (defaults to "chat")
        input_type: The input type (defaults to "chat")
        tweaks: Optional tweaks to customize the flow
        application_token: Optional application token for authentication
        file_path: Optional path to a file to upload
        components: Optional list of component IDs to upload the file to
        retry_on_auth_error: Whether to retry with a refreshed token on auth errors

    Returns:
        The JSON response from the flow
    """
    # Use default values if not provided
    endpoint = endpoint or ENDPOINT or FLOW_ID
    
    # If no token provided, try to get a valid one
    if application_token is None:
        logger.info("No token provided to run_langflow, attempting to get a valid token...")
        application_token = await get_valid_token()
        logger.info(f"Retrieved token length: {len(application_token) if application_token else 0}")
    
    tweaks = tweaks or DEFAULT_TWEAKS

    # Validate required credentials
    if not application_token:
        error_msg = "DataStax Langflow application token is missing. Please set DATASTAX_APPLICATION_TOKEN in your .env file."
        logger.error(error_msg)
        return {
            "error": True,
            "message": error_msg,
            "status_code": 401
        }
    
    if not endpoint:
        error_msg = "DataStax Langflow endpoint or flow ID is missing. Please set DATASTAX_ENDPOINT or DATASTAX_FLOW_ID in your .env file."
        logger.error(error_msg)
        return {
            "error": True,
            "message": error_msg,
            "status_code": 400
        }

    # Handle file upload if requested
    if file_path and components and HAS_LANGFLOW:
        try:
            tweaks = upload_file(
                file_path=file_path,
                host=BASE_API_URL,
                flow_id=endpoint,
                components=components,
                tweaks=tweaks
            )
            logger.info(f"Uploaded file {file_path} to components {components}")
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return {
                "error": True,
                "message": f"Failed to upload file: {str(e)}",
                "status_code": 500
            }

    # Construct API URL
    api_url = f"{BASE_API_URL}/lf/{LANGFLOW_ID}/api/v1/run/{endpoint}"
    
    # Log configuration for debugging
    logger.info(f"DataStax Langflow Configuration:")
    logger.info(f"  API URL: {BASE_API_URL}")
    logger.info(f"  Langflow ID: {LANGFLOW_ID}")
    logger.info(f"  Endpoint/Flow ID: {endpoint}")
    logger.info(f"  Full API URL: {api_url}")
    logger.info(f"  Token provided: {'Yes' if application_token else 'No'}")
    logger.info(f"  Token length: {len(application_token) if application_token else 0}")

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
        response = requests.post(api_url, json=payload, headers=headers)
        
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
        
        # Check for HTTP errors
        if response.status_code != 200:
            error_msg = f"DataStax Langflow API returned status code {response.status_code}"
            try:
                error_data = response.json()
                if isinstance(error_data, dict):
                    if "detail" in error_data:
                        error_msg = f"{error_msg}: {error_data['detail']}"
                    logger.error(f"Error response data: {error_data}")
            except Exception as e:
                error_msg = f"{error_msg}: {response.text[:200]}"
                logger.error(f"Failed to parse error response: {e}")
            
            logger.error(error_msg)
            return {
                "error": True,
                "message": error_msg,
                "status_code": response.status_code
            }
        
        # Return the JSON response
        return response.json()
    except requests.exceptions.RequestException as e:
        error_msg = f"Error calling DataStax Langflow API: {e}"
        logger.error(error_msg)
        # Return error response
        return {
            "error": True,
            "message": error_msg,
            "status_code": getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500
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
            output_type="json",
            input_type="json"
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
            logger.error(f"Raw response: {response}")
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
                                        if "text" in data:
                                            text_content = data["text"]
                                            
                                            # Try to parse recommendations from text
                                            try:
                                                # First, try to parse as JSON
                                                try:
                                                    parsed_json = json.loads(text_content)
                                                    if isinstance(parsed_json, list):
                                                        recommendations = parsed_json[:limit]
                                                    elif isinstance(parsed_json, dict) and "recommendations" in parsed_json:
                                                        recommendations = parsed_json.get("recommendations", [])[:limit]
                                                except json.JSONDecodeError:
                                                    # If not JSON, try to parse as text
                                                    # Look for numbered or bulleted lists
                                                    lines = text_content.split("\n")
                                                    current_rec = None
                                                    for line in lines:
                                                        line = line.strip()
                                                        # Check for numbered items or bullet points
                                                        if (line.startswith("1.") or line.startswith("•") or 
                                                            line.startswith("-") or line.startswith("*")):
                                                            # Start a new recommendation
                                                            if current_rec:
                                                                recommendations.append(current_rec)
                                                            
                                                            # Extract the name from the line
                                                            name = line.split(".", 1)[-1].strip() if "." in line else line[1:].strip()
                                                            current_rec = {
                                                                "name": name,
                                                                "description": "",
                                                                "ingredients": None,
                                                                "preparation": None,
                                                                "nutritional_info": None,
                                                                "cuisine_type": None,
                                                                "dietary_tags": None,
                                                                "confidence_score": None
                                                            }
                                                        elif current_rec and line:
                                                            # Add to the description of the current recommendation
                                                            if current_rec["description"]:
                                                                current_rec["description"] += " " + line
                                                            else:
                                                                current_rec["description"] = line
                                                    
                                                    # Add the last recommendation if it exists
                                                    if current_rec:
                                                        recommendations.append(current_rec)
                                            except Exception as e:
                                                logger.error(f"Error parsing recommendations from text: {e}")
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
        
        # If we still don't have recommendations, try the original approach
        if not recommendations:
            # Try the original approach with result key
            result = response.get("result", {})
            
            if isinstance(result, str):
                # If result is a string, try to parse it as JSON
                try:
                    parsed_result = json.loads(result)
                    if isinstance(parsed_result, list):
                        # If it's a list of recommendations
                        recommendations = parsed_result[:limit]
                    elif isinstance(parsed_result, dict) and "recommendations" in parsed_result:
                        # If it's a dict with a recommendations key
                        recommendations = parsed_result.get("recommendations", [])[:limit]
                except json.JSONDecodeError:
                    # If it's not valid JSON, it might be a text response
                    # Try to parse it as a text-based list of recommendations
                    recommendations = [{"name": item.strip(), "description": ""} 
                                      for item in result.split("\n") 
                                      if item.strip()][:limit]
            elif isinstance(result, list):
                # If result is already a list
                recommendations = result[:limit]
            elif isinstance(result, dict) and "recommendations" in result:
                # If result is a dict with recommendations
                recommendations = result.get("recommendations", [])[:limit]
    
    # Ensure each recommendation has the expected structure
    structured_recommendations = []
    for i, rec in enumerate(recommendations):
        if isinstance(rec, str):
            # If the recommendation is just a string, create a simple structure
            structured_recommendations.append({
                "name": rec,
                "description": None,
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