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
from src.services.langflow_service import run_langflow, get_ai_food_recommendations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_run_langflow():
    """Test the run_langflow function directly"""
    message = "Hello, I'm looking for healthy breakfast ideas"
    
    # Get configuration from environment variables
    endpoint = os.getenv("DATASTAX_ENDPOINT")
    token = os.getenv("DATASTAX_APPLICATION_TOKEN")
    
    logger.info(f"Testing run_langflow with endpoint: {endpoint}")
    logger.info(f"Token provided: {'Yes' if token else 'No'}")
    
    # Call the function
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
    
    logger.info(f"Testing get_ai_food_recommendations with query: {query}")
    
    # Call the function
    response = await get_ai_food_recommendations(
        query=query,
        user_preferences=user_preferences,
        limit=3
    )
    
    # Print the response
    logger.info("Response from get_ai_food_recommendations:")
    if not response.get("success"):
        logger.error(f"Error: {response.get('error')}")
    else:
        logger.info(f"Success! Recommendations: {json.dumps(response.get('recommendations'), indent=2)}")

async def main():
    """Run all tests"""
    logger.info("Starting DataStax Langflow integration tests")
    
    # Test run_langflow
    logger.info("\n=== Testing run_langflow ===")
    await test_run_langflow()
    
    # Test get_ai_food_recommendations
    logger.info("\n=== Testing get_ai_food_recommendations ===")
    await test_get_ai_food_recommendations()

if __name__ == "__main__":
    asyncio.run(main()) 