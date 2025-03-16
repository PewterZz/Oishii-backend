#!/usr/bin/env python
"""
Test script for DataStax Langflow integration.
This script directly tests the Langflow service without going through the API.
"""

import asyncio
import os
import json
import logging
from dotenv import load_dotenv
from src.services.langflow_service import run_langflow, get_ai_food_recommendations, get_valid_token, refresh_auth_token

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Verify environment variables are loaded
logger.info("Environment variables loaded:")
logger.info(f"DATASTAX_APPLICATION_TOKEN length: {len(os.getenv('DATASTAX_APPLICATION_TOKEN', ''))}")
logger.info(f"DATASTAX_REFRESH_TOKEN length: {len(os.getenv('DATASTAX_REFRESH_TOKEN', ''))}")
logger.info(f"DATASTAX_ENDPOINT: {os.getenv('DATASTAX_ENDPOINT', '')}")
logger.info(f"DATASTAX_FLOW_ID: {os.getenv('DATASTAX_FLOW_ID', '')}")

async def test_token_refresh():
    """Test the token refresh functionality"""
    logger.info("Testing token refresh functionality")
    
    # Get the current token
    current_token = os.getenv("DATASTAX_APPLICATION_TOKEN", "")
    refresh_token = os.getenv("DATASTAX_REFRESH_TOKEN", "")
    
    logger.info(f"Current application token length: {len(current_token) if current_token else 0}")
    logger.info(f"Current refresh token length: {len(refresh_token) if refresh_token else 0}")
    
    # Check if tokens are the same
    if current_token == refresh_token and current_token:
        logger.warning("Application token and refresh token are identical. This may cause refresh issues.")
    
    # Try to get a valid token (may refresh if needed)
    logger.info("Attempting to get a valid token...")
    valid_token = await get_valid_token()
    logger.info(f"Valid token length: {len(valid_token) if valid_token else 0}")
    
    # Force a token refresh
    logger.info("Forcing token refresh...")
    new_token = await refresh_auth_token()
    logger.info(f"New token length: {len(new_token) if new_token else 0}")
    
    # Check if token was refreshed
    if new_token and current_token and new_token != current_token:
        logger.info("Token was successfully refreshed")
    elif not new_token:
        logger.error("Token refresh failed - no token returned")
    elif not current_token:
        logger.warning("No original token to compare with")
    else:
        logger.warning("Token was not refreshed. This could be normal if the refresh token is invalid or not provided.")

async def test_run_langflow():
    """Test the run_langflow function directly"""
    message = "Hello, I'm looking for healthy breakfast ideas"
    
    # Get configuration from environment variables
    endpoint = os.getenv("DATASTAX_ENDPOINT", "")
    
    # Use get_valid_token instead of directly using the environment variable
    logger.info("Getting a valid token for run_langflow test...")
    token = await get_valid_token()
    
    logger.info(f"Testing run_langflow with endpoint: {endpoint}")
    logger.info(f"Token provided: {'Yes' if token else 'No'}")
    logger.info(f"Token length: {len(token) if token else 0}")
    
    # Check if we have the necessary configuration
    if not endpoint:
        logger.error("No endpoint configured. Cannot run test_run_langflow.")
        logger.error("Please set DATASTAX_ENDPOINT or DATASTAX_FLOW_ID in your .env file.")
        return
    
    if not token:
        logger.error("No valid token available. Cannot run test_run_langflow.")
        logger.error("Please set DATASTAX_APPLICATION_TOKEN and DATASTAX_REFRESH_TOKEN in your .env file.")
        return
    
    # Call the function
    logger.info(f"Calling run_langflow with message: '{message}'")
    response = await run_langflow(
        message=message,
        endpoint=endpoint,
        application_token=token
    )
    
    # Print the response
    logger.info("Response from run_langflow:")
    if response.get("error"):
        logger.error(f"Error: {response.get('message')}")
        logger.error(f"Status code: {response.get('status_code')}")
    else:
        logger.info(f"Success! Response: {json.dumps(response, indent=2)[:500]}...")

async def test_get_ai_food_recommendations():
    """Test the get_ai_food_recommendations function directly"""
    query = "healthy breakfast ideas"
    user_preferences = {
        "user_id": "test-user",
        "name": "Test User",
        "email": "test@example.com",
        "dietary_restrictions": ["vegetarian"],
        "allergies": ["nuts"],
        "cuisine_preferences": ["Mediterranean", "Asian"]
    }
    
    # Use get_valid_token instead of directly using the environment variable
    logger.info("Getting a valid token for get_ai_food_recommendations test...")
    token = await get_valid_token()
    
    logger.info(f"Testing get_ai_food_recommendations with query: {query}")
    logger.info(f"Token provided: {'Yes' if token else 'No'}")
    logger.info(f"Token length: {len(token) if token else 0}")
    
    # Check if we have a valid token
    if not token:
        logger.error("No valid token available. Cannot run test_get_ai_food_recommendations.")
        logger.error("Please set DATASTAX_APPLICATION_TOKEN and DATASTAX_REFRESH_TOKEN in your .env file.")
        return
    
    # Create some sample available foods
    available_foods = [
        {
            "name": "Greek Yogurt with Honey",
            "description": "Creamy Greek yogurt topped with honey and nuts",
            "category": "breakfast",
            "dietary_requirements": ["vegetarian", "gluten-free"],
            "allergens": ["dairy", "nuts"],
            "id": "sample-id-1"
        },
        {
            "name": "Avocado Toast",
            "description": "Whole grain toast topped with mashed avocado and seasonings",
            "category": "breakfast",
            "dietary_requirements": ["vegetarian", "vegan"],
            "allergens": ["gluten"],
            "id": "sample-id-2"
        }
    ]
    
    # Call the function
    logger.info(f"Calling get_ai_food_recommendations with query: '{query}'")
    response = await get_ai_food_recommendations(
        query=query,
        user_preferences=user_preferences,
        limit=3,
        application_token=token,
        available_foods=available_foods
    )
    
    # Print the response
    logger.info("Response from get_ai_food_recommendations:")
    if not response.get("success"):
        logger.error(f"Error: {response.get('error')}")
    else:
        logger.info(f"Success! Recommendations: {json.dumps(response.get('recommendations'), indent=2)}")

async def test_error_handling():
    """Test error handling with an invalid token"""
    message = "Test error handling"
    
    # Use an invalid token to test error handling
    invalid_token = "invalid_token"
    
    logger.info("Testing error handling with invalid token")
    
    # Call the function with retry_on_auth_error=True
    response = await run_langflow(
        message=message,
        application_token=invalid_token,
        retry_on_auth_error=True
    )
    
    # Print the response
    logger.info("Response from error handling test:")
    if response.get("error"):
        logger.info(f"Expected error received: {response.get('message')}")
        logger.info(f"Status code: {response.get('status_code')}")
    else:
        logger.warning("No error received with invalid token. This is unexpected.")

async def main():
    """Run all tests"""
    logger.info("Starting DataStax Langflow integration tests")
    
    # Test token refresh
    logger.info("\n=== Testing token refresh ===")
    await test_token_refresh()
    
    # Test run_langflow
    logger.info("\n=== Testing run_langflow ===")
    await test_run_langflow()
    
    # Test get_ai_food_recommendations
    logger.info("\n=== Testing get_ai_food_recommendations ===")
    await test_get_ai_food_recommendations()
    
    # Test error handling
    logger.info("\n=== Testing error handling ===")
    await test_error_handling()

if __name__ == "__main__":
    asyncio.run(main()) 