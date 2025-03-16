#!/usr/bin/env python
"""
Command-line utility to test the DataStax Langflow integration.

Usage:
    python -m src.utils.langflow_cli --query "healthy breakfast options" [--token YOUR_TOKEN]
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv
from src.services.langflow_service import run_langflow, get_ai_food_recommendations

# Load environment variables
load_dotenv()


async def main():
    parser = argparse.ArgumentParser(description="Test the DataStax Langflow integration")
    parser.add_argument("--query", type=str, required=True, help="The food query to send to the AI")
    parser.add_argument("--token", type=str, help="Your DataStax Application Token (overrides env variable)")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of recommendations")
    parser.add_argument("--preferences", action="store_true", help="Include sample user preferences")
    parser.add_argument("--raw", action="store_true", help="Use raw Langflow API instead of food recommendations")
    parser.add_argument("--file", type=str, help="Path to a file to upload (e.g., food image)")
    parser.add_argument("--components", type=str, help="Comma-separated list of component IDs to upload the file to")
    parser.add_argument("--output", type=str, help="Path to save the response as JSON")
    
    args = parser.parse_args()
    
    # Set application token if provided
    if args.token:
        os.environ["DATASTAX_APPLICATION_TOKEN"] = args.token
    
    try:
        if args.raw:
            # Use the raw Langflow API
            print(f"Sending query to DataStax Langflow: {args.query}")
            
            # Parse components if provided
            components = None
            if args.components:
                components = args.components.split(",")
            
            response = await run_langflow(
                message=args.query,
                file_path=args.file,
                components=components
            )
        else:
            # Use the food recommendations API
            sample_preferences = None
            if args.preferences:
                sample_preferences = {
                    "user_id": "sample-user",
                    "name": "Test User",
                    "dietary_restrictions": ["vegetarian"],
                    "allergies": ["peanuts"],
                    "cuisine_preferences": ["Italian", "Japanese"]
                }
                print(f"Including sample user preferences: {json.dumps(sample_preferences, indent=2)}")
            
            print(f"Getting AI food recommendations for: {args.query}")
            response = await get_ai_food_recommendations(
                query=args.query,
                user_preferences=sample_preferences,
                limit=args.limit,
                file_path=args.file
            )
        
        # Pretty print the response
        print("\nResponse:")
        formatted_response = json.dumps(response, indent=2)
        print(formatted_response)
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                f.write(formatted_response)
            print(f"\nResponse saved to {args.output}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 