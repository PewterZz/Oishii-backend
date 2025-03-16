#!/usr/bin/env python
"""
Test script for the template-based Dr. Foodlove implementation.
This script provides a colorful and well-formatted display of food recommendations.
"""

import asyncio
import json
import os
from src.services.dr_foodlove_service import get_dr_foodlove_recommendations

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    BG_BLUE = '\033[44m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_RED = '\033[41m'
    BG_PURPLE = '\033[45m'


def print_header(text):
    """Print a formatted header"""
    terminal_width = os.get_terminal_size().columns
    print(f"\n{Colors.BG_BLUE}{Colors.BOLD}{text.center(terminal_width)}{Colors.ENDC}")


def print_section(text):
    """Print a formatted section header"""
    print(f"\n{Colors.YELLOW}{Colors.BOLD}=== {text} ==={Colors.ENDC}")


def print_recommendation(rec, index):
    """Print a formatted food recommendation"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}🍽️  Recommendation #{index+1}: {rec['name']}{Colors.ENDC}")
    print(f"{Colors.GREEN}📝 Description:{Colors.ENDC} {rec['description']}")
    
    print(f"{Colors.GREEN}🥕 Ingredients:{Colors.ENDC}")
    for ingredient in rec['ingredients']:
        print(f"  • {ingredient}")
    
    print(f"{Colors.GREEN}👨‍🍳 Preparation:{Colors.ENDC} {rec['preparation']}")
    print(f"{Colors.GREEN}🍎 Nutritional Info:{Colors.ENDC} {rec['nutritional_info']}")
    print(f"{Colors.GREEN}🌍 Cuisine:{Colors.ENDC} {rec['cuisine_type']}")
    
    print(f"{Colors.GREEN}🏷️  Tags:{Colors.ENDC} {', '.join(rec['dietary_tags'])}")
    
    if 'health_benefits' in rec:
        print(f"{Colors.GREEN}💪 Health Benefits:{Colors.ENDC} {', '.join(rec['health_benefits'])}")


def print_health_insights(insights):
    """Print formatted health insights"""
    print(f"\n{Colors.BG_PURPLE}{Colors.BOLD} 🩺 HEALTH INSIGHTS {Colors.ENDC}")
    print(f"{Colors.GREEN}🔄 Variety Score:{Colors.ENDC} {insights['variety']}")
    print(f"{Colors.GREEN}⚖️  Balance Score:{Colors.ENDC} {insights['balance_score']}/5")
    
    if insights['nutrient_focus']:
        print(f"{Colors.GREEN}🎯 Nutrient Focus:{Colors.ENDC} {', '.join(insights['nutrient_focus'])}")
    
    if insights.get('recommendations'):
        print(f"\n{Colors.YELLOW}💡 Health Recommendations:{Colors.ENDC}")
        for rec in insights['recommendations']:
            print(f"  • {rec}")


async def test_dr_foodlove():
    """Test the Dr. Foodlove template-based recommendations with beautiful formatting"""
    
    print_header(" 🍲 DR. FOODLOVE RECOMMENDATION TESTER 🍲 ")
    
    # Test different query types
    queries = [
        "healthy breakfast ideas",
        "quick dinner recipes",
        "vegetarian meal options",
        "nutritious lunch ideas",
        "easy breakfast recipes"
    ]
    
    for query in queries:
        print_section(f"Testing query: '{query}'")
        
        # Get recommendations
        response = await get_dr_foodlove_recommendations(
            query=query,
            detailed_response=True,
            limit=3
        )
        
        # Print results
        print(f"{Colors.GREEN}✅ Success:{Colors.ENDC} {response['success']}")
        print(f"{Colors.GREEN}📊 Number of recommendations:{Colors.ENDC} {len(response['recommendations'])}")
        
        # Print each recommendation
        for i, rec in enumerate(response['recommendations']):
            print_recommendation(rec, i)
        
        # Print health insights
        if response.get('health_insights'):
            print_health_insights(response['health_insights'])
        
        # Separator between queries
        terminal_width = os.get_terminal_size().columns
        print(f"\n{Colors.BLUE}{'-' * terminal_width}{Colors.ENDC}")


if __name__ == "__main__":
    try:
        asyncio.run(test_dr_foodlove())
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Test interrupted by user.{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {str(e)}{Colors.ENDC}")
    finally:
        print(f"\n{Colors.GREEN}Test completed.{Colors.ENDC}") 