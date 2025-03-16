#!/usr/bin/env python
"""
Command-line utility to test the Dr. Foodlove AI integration.

Usage:
    python -m src.utils.dr_foodlove_cli --query "healthy breakfast options" [--token YOUR_TOKEN]
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
from src.services.dr_foodlove_service import get_dr_foodlove_recommendations

# Load environment variables
load_dotenv()


async def main():
    parser = argparse.ArgumentParser(description="Test the Dr. Foodlove AI integration")
    parser.add_argument("--query", type=str, required=True, help="The food query to send to Dr. Foodlove")
    parser.add_argument("--token", type=str, help="Your DataStax Application Token (overrides env variable)")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of recommendations")
    parser.add_argument("--preferences", action="store_true", help="Include sample user preferences")
    parser.add_argument("--detailed", action="store_true", help="Include detailed health insights")
    parser.add_argument("--image", type=str, help="Path to a food image to analyze")
    parser.add_argument("--output", type=str, help="Path to save the response as JSON")
    parser.add_argument("--health-goals", type=str, help="Comma-separated list of health goals")
    
    args = parser.parse_args()
    
    # Set application token if provided
    if args.token:
        os.environ["DATASTAX_APPLICATION_TOKEN"] = args.token
    
    try:
        # Use the Dr. Foodlove recommendations API
        sample_preferences = None
        if args.preferences:
            sample_preferences = {
                "user_id": "sample-user",
                "name": "Test User",
                "dietary_restrictions": ["vegetarian"],
                "allergies": ["peanuts"],
                "cuisine_preferences": ["Italian", "Japanese"]
            }
            
            # Add health goals if provided
            if args.health_goals:
                sample_preferences["health_goals"] = args.health_goals.split(",")
                
            print(f"Including sample user preferences: {json.dumps(sample_preferences, indent=2)}")
        
        print(f"Getting Dr. Foodlove recommendations for: {args.query}")
        response = await get_dr_foodlove_recommendations(
            query=args.query,
            user_preferences=sample_preferences,
            limit=args.limit,
            food_image_path=args.image,
            detailed_response=args.detailed
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
        
        # Print health insights if available
        if args.detailed and response.get("health_insights"):
            print("\nHealth Insights:")
            insights = response["health_insights"]
            print(f"Variety Score: {insights.get('variety', 0)}")
            print(f"Balance Score: {insights.get('balance_score', 0)}/5")
            print(f"Nutrient Focus: {', '.join(insights.get('nutrient_focus', []))}")
            print("\nRecommendations:")
            for rec in insights.get("recommendations", []):
                print(f"- {rec}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 