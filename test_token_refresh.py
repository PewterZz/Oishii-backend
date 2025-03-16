#!/usr/bin/env python
"""
Test script specifically for DataStax token refresh functionality.
This script tests different approaches to token refresh and validation.
"""

import asyncio
import os
import json
import logging
import requests
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# DataStax configuration
BASE_API_URL = os.getenv("DATASTAX_LANGFLOW_API_URL", "https://api.langflow.astra.datastax.com")
LANGFLOW_ID = os.getenv("DATASTAX_LANGFLOW_ID", "f97d1e16-3dd8-4355-99fa-e8f1b98563ae")
FLOW_ID = os.getenv("DATASTAX_FLOW_ID", "567ad106-a9f3-4e30-b909-628e89186549")
APPLICATION_TOKEN = os.getenv("DATASTAX_APPLICATION_TOKEN", "")
REFRESH_TOKEN = os.getenv("DATASTAX_REFRESH_TOKEN", "")

# Verify environment variables are loaded
logger.info("Environment variables loaded:")
logger.info(f"DATASTAX_APPLICATION_TOKEN length: {len(APPLICATION_TOKEN)}")
logger.info(f"DATASTAX_REFRESH_TOKEN length: {len(REFRESH_TOKEN)}")
logger.info(f"DATASTAX_LANGFLOW_API_URL: {BASE_API_URL}")
logger.info(f"DATASTAX_LANGFLOW_ID: {LANGFLOW_ID}")
logger.info(f"DATASTAX_FLOW_ID: {FLOW_ID}")

# Check if tokens are the same
if APPLICATION_TOKEN == REFRESH_TOKEN:
    logger.warning("WARNING: Application token and refresh token are identical. This may cause refresh issues.")


async def test_token_validation():
    """Test token validation endpoint"""
    logger.info("\n=== Testing token validation ===")
    
    validation_url = f"{BASE_API_URL}/lf/{LANGFLOW_ID}/api/v1/validate"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {APPLICATION_TOKEN}"
    }
    
    try:
        logger.info(f"Calling validation endpoint: {validation_url}")
        response = requests.get(validation_url, headers=headers, timeout=10)
        
        logger.info(f"Validation response status code: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("Token is valid!")
            try:
                data = response.json()
                logger.info(f"Validation response: {json.dumps(data, indent=2)}")
            except:
                logger.info(f"Validation response: {response.text[:100]}...")
        else:
            logger.error(f"Token validation failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text[:200]}...")
    except Exception as e:
        logger.error(f"Error during token validation: {e}")


async def test_refresh_approach_1():
    """Test standard OAuth refresh approach"""
    logger.info("\n=== Testing refresh approach 1 (Standard OAuth) ===")
    
    refresh_url = f"{BASE_API_URL}/auth/refresh"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {REFRESH_TOKEN}"
    }
    
    payload = {
        "refresh_token": REFRESH_TOKEN
    }
    
    try:
        logger.info(f"Calling refresh endpoint: {refresh_url}")
        response = requests.post(refresh_url, headers=headers, json=payload, timeout=10)
        
        logger.info(f"Refresh response status code: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("Token refresh successful!")
            try:
                data = response.json()
                logger.info(f"Refresh response: {json.dumps(data, indent=2)}")
                
                # Check for token in response
                if "access_token" in data:
                    logger.info(f"New access token received. Length: {len(data['access_token'])}")
                elif "token" in data:
                    logger.info(f"New token received. Length: {len(data['token'])}")
                else:
                    logger.warning("No token found in response")
            except:
                logger.info(f"Refresh response: {response.text[:100]}...")
        else:
            logger.error(f"Token refresh failed with status code: {response.status_code}")
            if "<!DOCTYPE HTML" in response.text:
                logger.error("CloudFront error detected. This may indicate IP restrictions or rate limiting.")
            else:
                logger.error(f"Response: {response.text[:200]}...")
    except Exception as e:
        logger.error(f"Error during token refresh: {e}")


async def test_refresh_approach_2():
    """Test DataStax specific refresh approach"""
    logger.info("\n=== Testing refresh approach 2 (DataStax specific) ===")
    
    refresh_url = f"{BASE_API_URL}/api/token/refresh"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "token": REFRESH_TOKEN
    }
    
    try:
        logger.info(f"Calling refresh endpoint: {refresh_url}")
        response = requests.post(refresh_url, headers=headers, json=payload, timeout=10)
        
        logger.info(f"Refresh response status code: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("Token refresh successful!")
            try:
                data = response.json()
                logger.info(f"Refresh response: {json.dumps(data, indent=2)}")
                
                # Check for token in response
                if "access_token" in data:
                    logger.info(f"New access token received. Length: {len(data['access_token'])}")
                elif "token" in data:
                    logger.info(f"New token received. Length: {len(data['token'])}")
                else:
                    logger.warning("No token found in response")
            except:
                logger.info(f"Refresh response: {response.text[:100]}...")
        else:
            logger.error(f"Token refresh failed with status code: {response.status_code}")
            if "<!DOCTYPE HTML" in response.text:
                logger.error("CloudFront error detected. This may indicate IP restrictions or rate limiting.")
            else:
                logger.error(f"Response: {response.text[:200]}...")
    except Exception as e:
        logger.error(f"Error during token refresh: {e}")


async def test_refresh_approach_3():
    """Test using refresh token as application token"""
    logger.info("\n=== Testing refresh approach 3 (Using refresh token as application token) ===")
    
    validation_url = f"{BASE_API_URL}/lf/{LANGFLOW_ID}/api/v1/validate"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {REFRESH_TOKEN}"
    }
    
    try:
        logger.info(f"Calling validation endpoint with refresh token: {validation_url}")
        response = requests.get(validation_url, headers=headers, timeout=10)
        
        logger.info(f"Validation response status code: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("Refresh token is valid as an application token!")
            try:
                data = response.json()
                logger.info(f"Validation response: {json.dumps(data, indent=2)}")
            except:
                logger.info(f"Validation response: {response.text[:100]}...")
        else:
            logger.error(f"Validation with refresh token failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text[:200]}...")
    except Exception as e:
        logger.error(f"Error during validation with refresh token: {e}")


async def test_simple_api_call():
    """Test a simple API call to verify token works"""
    logger.info("\n=== Testing simple API call ===")
    
    api_url = f"{BASE_API_URL}/lf/{LANGFLOW_ID}/api/v1/run/{FLOW_ID}"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {APPLICATION_TOKEN}"
    }
    
    payload = {
        "input_value": "Hello, testing token",
        "input_type": "text",
        "output_type": "text"
    }
    
    try:
        logger.info(f"Calling API endpoint: {api_url}")
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        
        logger.info(f"API response status code: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("API call successful!")
            try:
                data = response.json()
                logger.info(f"API response: {json.dumps(data, indent=2)[:500]}...")
            except:
                logger.info(f"API response: {response.text[:100]}...")
        else:
            logger.error(f"API call failed with status code: {response.status_code}")
            try:
                error_data = response.json()
                logger.error(f"Error response: {json.dumps(error_data, indent=2)}")
            except:
                logger.error(f"Response: {response.text[:200]}...")
    except Exception as e:
        logger.error(f"Error during API call: {e}")


async def main():
    """Run all tests"""
    logger.info("Starting DataStax token refresh tests")
    
    # Test token validation
    await test_token_validation()
    
    # Test refresh approaches
    await test_refresh_approach_1()
    await test_refresh_approach_2()
    await test_refresh_approach_3()
    
    # Test API call
    await test_simple_api_call()
    
    logger.info("\nAll tests completed")


if __name__ == "__main__":
    asyncio.run(main()) 