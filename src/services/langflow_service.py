import os
import json
import logging
import requests
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DataStax Langflow configuration
BASE_API_URL = os.getenv("DATASTAX_LANGFLOW_API_URL", "https://api.langflow.astra.datastax.com")
LANGFLOW_ID = os.getenv("DATASTAX_LANGFLOW_ID", "f97d1e16-3dd8-4355-99fa-e8f1b98563ae")
FLOW_ID = os.getenv("DATASTAX_FLOW_ID", "567ad106-a9f3-4e30-b909-628e89186549")
APPLICATION_TOKEN = os.getenv("DATASTAX_APPLICATION_TOKEN", "")
ENDPOINT = os.getenv("DATASTAX_ENDPOINT", "")  # You can set a specific endpoint name in the flow settings

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


async def run_langflow(
    message: str,
    endpoint: Optional[str] = None,
    output_type: str = "chat",
    input_type: str = "chat",
    tweaks: Optional[Dict[str, Any]] = None,
    application_token: Optional[str] = None,
    file_path: Optional[str] = None,
    components: Optional[List[str]] = None
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

    Returns:
        The JSON response from the flow
    """
    # Use default values if not provided
    endpoint = endpoint or ENDPOINT or FLOW_ID
    application_token = application_token or APPLICATION_TOKEN
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
    application_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get AI-powered food recommendations using DataStax Langflow.
    
    Args:
        query: The user's food query or request
        user_preferences: Optional user preferences to customize recommendations
        limit: Maximum number of recommendations to return
        file_path: Optional path to a file (e.g., image of food) to analyze
        application_token: Optional application token for authentication (defaults to env variable)
        
    Returns:
        Dictionary containing AI recommendations and metadata
    """
    # Log the function call
    logger.info(f"get_ai_food_recommendations called with query: '{query[:100]}...'")
    logger.info(f"User preferences provided: {user_preferences is not None}")
    
    # Use default token if not provided
    application_token = application_token or APPLICATION_TOKEN
    
    # Check if token is available
    if not application_token:
        error_msg = "DataStax Langflow application token is missing"
        logger.error(error_msg)
        return {
            "success": False,
            "query": query,
            "recommendations": [],
            "user_preferences_applied": user_preferences is not None,
            "error": error_msg
        }
    
    # Construct a more detailed prompt if user preferences are provided
    if user_preferences:
        # Format user preferences into a readable string
        preferences_str = json.dumps(user_preferences, indent=2)
        message = f"Based on these preferences:\n{preferences_str}\n\nPlease recommend {limit} food options for: {query}"
    else:
        message = f"Please recommend {limit} food options for: {query}"
    
    # Determine if we need to upload a file
    components = None
    if file_path:
        # Assuming the file should be uploaded to a component that handles images
        # You would need to adjust this based on your actual flow configuration
        components = ["ImageComponent-XYZ"]  # Replace with actual component ID
    
    try:
        # Call the Langflow API
        logger.info(f"Calling run_langflow with query length: {len(query)}")
        response = await run_langflow(
            message=message,
            file_path=file_path,
            components=components,
            application_token=application_token
        )
        
        # Log the raw response for debugging
        logger.info(f"Raw response from run_langflow: {json.dumps(response)[:500]}...")
        
        # Check for errors in the response
        if response.get("error"):
            error_msg = f"Error from DataStax Langflow: {response.get('message', 'Unknown error')}"
            logger.error(error_msg)
            return {
                "success": False,
                "query": query,
                "recommendations": [],
                "user_preferences_applied": user_preferences is not None,
                "error": error_msg
            }
        
        # Process the response
        try:
            # Extract the recommendations from the response
            recommendations = process_ai_recommendations(response, limit)
            
            # Log the number of recommendations
            logger.info(f"Processed {len(recommendations)} recommendations")
            
            # Return the formatted response
            return {
                "success": True,
                "query": query,
                "recommendations": recommendations,
                "user_preferences_applied": user_preferences is not None
            }
        except Exception as e:
            error_msg = f"Error processing AI recommendations: {e}"
            logger.error(error_msg)
            logger.error(f"Response that caused the error: {json.dumps(response)[:500]}...")
            return {
                "success": False,
                "query": query,
                "recommendations": [],
                "user_preferences_applied": user_preferences is not None,
                "error": error_msg
            }
    except Exception as e:
        error_msg = f"Error calling DataStax Langflow: {e}"
        logger.error(error_msg)
        return {
            "success": False,
            "query": query,
            "recommendations": [],
            "user_preferences_applied": user_preferences is not None,
            "error": error_msg
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
    
    # Extract recommendations from the response
    # The exact structure will depend on your Langflow output format
    # This is a simplified example - adjust based on your actual response structure
    
    if isinstance(response, dict):
        # If the response is a dictionary with a 'result' key (common format)
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
    
    return structured_recommendations 