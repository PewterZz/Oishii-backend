#!/usr/bin/env python
"""
Meal Swap Demo for Oishii Platform

This script demonstrates how students can swap meals with each other
using a simple command-line interface with colorful formatting.
"""

import asyncio
import json
import os
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

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
    BG_CYAN = '\033[46m'

# Sample student data
STUDENTS = [
    {"id": "s1001", "name": "Alex Johnson", "email": "alex.j@university.edu", "dietary_preferences": ["vegetarian"]},
    {"id": "s1002", "name": "Jamie Smith", "email": "jamie.s@university.edu", "dietary_preferences": ["gluten-free"]},
    {"id": "s1003", "name": "Taylor Brown", "email": "taylor.b@university.edu", "dietary_preferences": ["dairy-free"]},
    {"id": "s1004", "name": "Morgan Lee", "email": "morgan.l@university.edu", "dietary_preferences": ["vegan"]},
    {"id": "s1005", "name": "Casey Wilson", "email": "casey.w@university.edu", "dietary_preferences": ["pescatarian"]}
]

# Sample meal data
MEALS = [
    {
        "id": "m1001",
        "name": "Mediterranean Quinoa Bowl",
        "description": "A nutritious bowl featuring protein-rich quinoa, fresh vegetables, and heart-healthy olive oil.",
        "ingredients": ["quinoa", "cucumber", "cherry tomatoes", "red onion", "feta cheese", "kalamata olives", "olive oil"],
        "dietary_tags": ["vegetarian", "high-protein"],
        "cuisine_type": "Mediterranean",
        "student_id": "s1001",
        "meal_time": "lunch",
        "available_for_swap": True
    },
    {
        "id": "m1002",
        "name": "Grilled Salmon with Roasted Vegetables",
        "description": "Omega-3 rich salmon fillet served with a colorful medley of roasted seasonal vegetables.",
        "ingredients": ["salmon fillet", "zucchini", "bell peppers", "cherry tomatoes", "red onion", "olive oil"],
        "dietary_tags": ["gluten-free", "high-protein", "pescatarian"],
        "cuisine_type": "Mediterranean",
        "student_id": "s1002",
        "meal_time": "dinner",
        "available_for_swap": True
    },
    {
        "id": "m1003",
        "name": "Chickpea and Spinach Curry",
        "description": "A fragrant curry featuring protein-rich chickpeas and iron-packed spinach in a creamy tomato-based sauce.",
        "ingredients": ["chickpeas", "spinach", "onion", "garlic", "ginger", "tomatoes", "coconut milk", "curry spices"],
        "dietary_tags": ["vegan", "gluten-free", "dairy-free"],
        "cuisine_type": "Indian",
        "student_id": "s1004",
        "meal_time": "dinner",
        "available_for_swap": True
    },
    {
        "id": "m1004",
        "name": "Avocado Toast with Poached Egg",
        "description": "Whole grain toast topped with creamy avocado, a perfectly poached egg, and a sprinkle of microgreens.",
        "ingredients": ["whole grain bread", "avocado", "eggs", "microgreens", "lemon juice", "red pepper flakes"],
        "dietary_tags": ["vegetarian", "high-protein"],
        "cuisine_type": "Modern",
        "student_id": "s1003",
        "meal_time": "breakfast",
        "available_for_swap": True
    },
    {
        "id": "m1005",
        "name": "Tuna and White Bean Salad",
        "description": "A protein-packed salad combining tuna, white beans, and fresh vegetables.",
        "ingredients": ["canned tuna", "cannellini beans", "red onion", "cherry tomatoes", "arugula", "lemon juice", "olive oil"],
        "dietary_tags": ["dairy-free", "gluten-free", "high-protein"],
        "cuisine_type": "Mediterranean",
        "student_id": "s1005",
        "meal_time": "lunch",
        "available_for_swap": True
    }
]

# Sample swap requests
SWAP_REQUESTS = []

def print_header(text):
    """Print a formatted header"""
    terminal_width = os.get_terminal_size().columns
    print(f"\n{Colors.BG_BLUE}{Colors.BOLD}{text.center(terminal_width)}{Colors.ENDC}")

def print_section(text):
    """Print a formatted section header"""
    print(f"\n{Colors.YELLOW}{Colors.BOLD}=== {text} ==={Colors.ENDC}")

def print_meal(meal, show_student=True):
    """Print a formatted meal"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}🍽️  {meal['name']}{Colors.ENDC}")
    print(f"{Colors.GREEN}📝 Description:{Colors.ENDC} {meal['description']}")
    
    print(f"{Colors.GREEN}🥕 Ingredients:{Colors.ENDC}")
    for ingredient in meal['ingredients']:
        print(f"  • {ingredient}")
    
    print(f"{Colors.GREEN}🌍 Cuisine:{Colors.ENDC} {meal['cuisine_type']}")
    print(f"{Colors.GREEN}🕒 Meal Time:{Colors.ENDC} {meal['meal_time'].capitalize()}")
    print(f"{Colors.GREEN}🏷️  Tags:{Colors.ENDC} {', '.join(meal['dietary_tags'])}")
    
    if show_student:
        student = next((s for s in STUDENTS if s['id'] == meal['student_id']), None)
        if student:
            print(f"{Colors.GREEN}👤 Owner:{Colors.ENDC} {student['name']}")

def print_student(student):
    """Print formatted student information"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}👤 {student['name']}{Colors.ENDC}")
    print(f"{Colors.GREEN}📧 Email:{Colors.ENDC} {student['email']}")
    print(f"{Colors.GREEN}🍽️ Dietary Preferences:{Colors.ENDC} {', '.join(student['dietary_preferences'])}")
    
    # Get student's meals
    student_meals = [m for m in MEALS if m['student_id'] == student['id']]
    if student_meals:
        print(f"{Colors.GREEN}🥗 Meals:{Colors.ENDC}")
        for meal in student_meals:
            print(f"  • {meal['name']} ({meal['meal_time'].capitalize()})")

def print_swap_request(swap_request):
    """Print a formatted swap request"""
    requester = next((s for s in STUDENTS if s['id'] == swap_request['requester_id']), None)
    owner = next((s for s in STUDENTS if s['id'] == swap_request['owner_id']), None)
    requested_meal = next((m for m in MEALS if m['id'] == swap_request['requested_meal_id']), None)
    offered_meal = next((m for m in MEALS if m['id'] == swap_request['offered_meal_id']), None)
    
    status_colors = {
        "pending": Colors.YELLOW,
        "accepted": Colors.GREEN,
        "rejected": Colors.RED
    }
    
    print(f"\n{Colors.BG_CYAN}{Colors.BOLD} SWAP REQUEST #{swap_request['id']} {Colors.ENDC}")
    print(f"{Colors.GREEN}📅 Date:{Colors.ENDC} {swap_request['date']}")
    print(f"{Colors.GREEN}👤 Requester:{Colors.ENDC} {requester['name']}")
    print(f"{Colors.GREEN}👤 Meal Owner:{Colors.ENDC} {owner['name']}")
    print(f"{Colors.GREEN}🍽️ Requested Meal:{Colors.ENDC} {requested_meal['name']} ({requested_meal['meal_time'].capitalize()})")
    print(f"{Colors.GREEN}🍽️ Offered Meal:{Colors.ENDC} {offered_meal['name']} ({offered_meal['meal_time'].capitalize()})")
    
    status_color = status_colors.get(swap_request['status'], Colors.BLUE)
    print(f"{Colors.GREEN}📊 Status:{Colors.ENDC} {status_color}{swap_request['status'].upper()}{Colors.ENDC}")
    
    if swap_request.get('message'):
        print(f"{Colors.GREEN}💬 Message:{Colors.ENDC} \"{swap_request['message']}\"")

def list_available_meals():
    """List all meals available for swapping"""
    print_section("Available Meals for Swapping")
    
    available_meals = [m for m in MEALS if m['available_for_swap']]
    if not available_meals:
        print(f"{Colors.YELLOW}No meals are currently available for swapping.{Colors.ENDC}")
        return
    
    for meal in available_meals:
        print_meal(meal)

def list_students():
    """List all students"""
    print_section("Registered Students")
    
    for student in STUDENTS:
        print_student(student)

def create_swap_request(requester_id, requested_meal_id, offered_meal_id, message=""):
    """Create a new swap request"""
    # Validate that the meals exist and are available
    requested_meal = next((m for m in MEALS if m['id'] == requested_meal_id), None)
    offered_meal = next((m for m in MEALS if m['id'] == offered_meal_id), None)
    
    if not requested_meal or not offered_meal:
        print(f"{Colors.RED}Error: One or both meals do not exist.{Colors.ENDC}")
        return None
    
    if not requested_meal['available_for_swap'] or not offered_meal['available_for_swap']:
        print(f"{Colors.RED}Error: One or both meals are not available for swapping.{Colors.ENDC}")
        return None
    
    if requested_meal['student_id'] == requester_id:
        print(f"{Colors.RED}Error: You cannot request your own meal.{Colors.ENDC}")
        return None
    
    if offered_meal['student_id'] != requester_id:
        print(f"{Colors.RED}Error: You can only offer your own meals.{Colors.ENDC}")
        return None
    
    # Create the swap request
    swap_request = {
        "id": f"sr{len(SWAP_REQUESTS) + 1001}",
        "requester_id": requester_id,
        "owner_id": requested_meal['student_id'],
        "requested_meal_id": requested_meal_id,
        "offered_meal_id": offered_meal_id,
        "status": "pending",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "message": message
    }
    
    SWAP_REQUESTS.append(swap_request)
    return swap_request

def respond_to_swap_request(swap_request_id, accept=True):
    """Accept or reject a swap request"""
    swap_request = next((sr for sr in SWAP_REQUESTS if sr['id'] == swap_request_id), None)
    
    if not swap_request:
        print(f"{Colors.RED}Error: Swap request not found.{Colors.ENDC}")
        return False
    
    if swap_request['status'] != "pending":
        print(f"{Colors.RED}Error: This swap request has already been {swap_request['status']}.{Colors.ENDC}")
        return False
    
    # Update the swap request status
    swap_request['status'] = "accepted" if accept else "rejected"
    
    # If accepted, swap the meals' ownership
    if accept:
        requested_meal = next((m for m in MEALS if m['id'] == swap_request['requested_meal_id']), None)
        offered_meal = next((m for m in MEALS if m['id'] == swap_request['offered_meal_id']), None)
        
        if requested_meal and offered_meal:
            # Swap student IDs
            temp_id = requested_meal['student_id']
            requested_meal['student_id'] = offered_meal['student_id']
            offered_meal['student_id'] = temp_id
            
            # Mark as not available for swap anymore
            requested_meal['available_for_swap'] = False
            offered_meal['available_for_swap'] = False
    
    return True

async def simulate_meal_swap():
    """Simulate the meal swapping process"""
    print_header(" 🔄 OISHII MEAL SWAP DEMONSTRATION 🔄 ")
    
    # Step 1: Show all students
    print_header(" 👥 REGISTERED STUDENTS 👥 ")
    list_students()
    
    # Step 2: Show available meals
    print_header(" 🍽️ AVAILABLE MEALS FOR SWAPPING 🍽️ ")
    list_available_meals()
    
    # Step 3: Create a swap request
    print_header(" 🔄 CREATING A SWAP REQUEST 🔄 ")
    
    requester = STUDENTS[0]  # Alex
    requested_meal = next((m for m in MEALS if m['student_id'] != requester['id']), None)  # Jamie's meal
    offered_meal = next((m for m in MEALS if m['student_id'] == requester['id']), None)  # Alex's meal
    
    print(f"{Colors.BOLD}Alex wants to swap their {offered_meal['name']} for {requested_meal['name']}{Colors.ENDC}")
    
    # Show the meals being swapped
    print_section("Requested Meal (Currently owned by Jamie)")
    print_meal(requested_meal)
    
    print_section("Offered Meal (Currently owned by Alex)")
    print_meal(offered_meal)
    
    # Create the swap request
    swap_request = create_swap_request(
        requester_id=requester['id'],
        requested_meal_id=requested_meal['id'],
        offered_meal_id=offered_meal['id'],
        message="Hi! I'd love to try your meal. Would you like to swap with mine?"
    )
    
    if swap_request:
        print(f"\n{Colors.GREEN}✅ Swap request created successfully!{Colors.ENDC}")
        print_swap_request(swap_request)
        
        # Simulate waiting for response
        print(f"\n{Colors.YELLOW}Waiting for Jamie to respond to the swap request...{Colors.ENDC}")
        for i in range(3):
            print(".", end="", flush=True)
            await asyncio.sleep(1)
        print()
        
        # Step 4: Accept the swap request
        print_header(" ✅ ACCEPTING THE SWAP REQUEST ✅ ")
        
        if respond_to_swap_request(swap_request['id'], accept=True):
            print(f"\n{Colors.GREEN}✅ Jamie has accepted the swap request!{Colors.ENDC}")
            
            # Update the swap request in our list
            updated_swap_request = next((sr for sr in SWAP_REQUESTS if sr['id'] == swap_request['id']), None)
            print_swap_request(updated_swap_request)
            
            # Step 5: Show the updated meal ownership
            print_header(" 🔄 UPDATED MEAL OWNERSHIP 🔄 ")
            
            # Show Alex's updated meals
            alex = next((s for s in STUDENTS if s['id'] == requester['id']), None)
            print_section(f"{alex['name']}'s Meals After Swap")
            alex_meals = [m for m in MEALS if m['student_id'] == alex['id']]
            for meal in alex_meals:
                print_meal(meal, show_student=False)
            
            # Show Jamie's updated meals
            jamie = next((s for s in STUDENTS if s['id'] == requested_meal['student_id']), None)
            print_section(f"{jamie['name']}'s Meals After Swap")
            jamie_meals = [m for m in MEALS if m['student_id'] == jamie['id']]
            for meal in jamie_meals:
                print_meal(meal, show_student=False)
    
    # Step 6: Show a summary of all swap requests
    print_header(" 📊 SWAP REQUESTS SUMMARY 📊 ")
    
    if SWAP_REQUESTS:
        for swap_request in SWAP_REQUESTS:
            print_swap_request(swap_request)
    else:
        print(f"{Colors.YELLOW}No swap requests have been made yet.{Colors.ENDC}")
    
    print_header(" 🎉 MEAL SWAP DEMONSTRATION COMPLETED 🎉 ")
    print(f"\n{Colors.GREEN}The Oishii platform makes it easy for students to swap meals based on their preferences and dietary needs.{Colors.ENDC}")
    print(f"{Colors.GREEN}This feature promotes food variety, reduces waste, and builds community among students.{Colors.ENDC}")

if __name__ == "__main__":
    try:
        asyncio.run(simulate_meal_swap())
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Demonstration interrupted by user.{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {str(e)}{Colors.ENDC}")
    finally:
        print(f"\n{Colors.GREEN}Demonstration completed.{Colors.ENDC}") 