import os
import json
import logging
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from .langflow_service import run_langflow, get_ai_food_recommendations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dr. Foodlove specific configuration
DR_FOODLOVE_PROMPT_TEMPLATE = """
You are Dr. Foodlove, an AI nutritionist and food expert. 
Based on the following information, provide personalized food recommendations:

Query: {query}

{preferences_section}

{available_foods_section}

IMPORTANT GUIDELINES:
1. ONLY recommend foods that are likely to exist in a typical food database.
2. DO NOT invent fictional dishes or make up random food items.
3. Provide recommendations in a structured format as shown below.
4. Focus on real, common dishes that match the user's query and preferences.
5. Include nutritional benefits where relevant.
6. If dietary restrictions are provided, strictly adhere to them.
7. If available foods are provided, prioritize recommending those foods.

Please provide {limit} food recommendations that are:
1. Nutritionally balanced
2. Aligned with the user's preferences and restrictions
3. Practical to prepare
4. Varied in cuisine types

YOUR RESPONSE MUST BE IN THIS JSON FORMAT:
```json
[
  {{
    "name": "Specific Dish Name",
    "description": "Brief description of the dish and why it matches the query",
    "ingredients": ["ingredient1", "ingredient2", "ingredient3"],
    "preparation": "Brief preparation method (optional)",
    "nutritional_info": "Brief nutritional highlights",
    "cuisine_type": "Cuisine category",
    "dietary_tags": ["tag1", "tag2"],
    "food_id": "ID of the food in the database (if available)"
  }},
  {{
    // Additional recommendations...
  }}
]
```

DO NOT include any text outside the JSON structure. Your entire response should be valid JSON that can be parsed programmatically.
"""

# Template responses for different food queries
TEMPLATE_RESPONSES = {
    "default": [
        {
            "name": "Mediterranean Quinoa Bowl",
            "description": "A nutritious bowl featuring protein-rich quinoa, fresh vegetables, and heart-healthy olive oil. Perfect for a balanced meal that provides sustained energy.",
            "ingredients": ["quinoa", "cucumber", "cherry tomatoes", "red onion", "feta cheese", "kalamata olives", "extra virgin olive oil", "lemon juice", "fresh herbs"],
            "preparation": "Cook quinoa according to package instructions. Combine with chopped vegetables, olives, and feta. Dress with olive oil and lemon juice. Garnish with fresh herbs.",
            "nutritional_info": "High in protein, fiber, and essential minerals. Contains heart-healthy fats from olive oil.",
            "cuisine_type": "Mediterranean",
            "dietary_tags": ["vegetarian", "gluten-free", "high-protein"],
            "health_benefits": ["heart health", "digestive health", "sustained energy"]
        },
        {
            "name": "Miso Glazed Salmon",
            "description": "Tender salmon fillets glazed with a sweet and savory miso mixture. Rich in omega-3 fatty acids and high-quality protein.",
            "ingredients": ["salmon fillets", "white miso paste", "honey", "soy sauce", "rice vinegar", "ginger", "garlic", "sesame seeds", "green onions"],
            "preparation": "Mix miso, honey, soy sauce, and rice vinegar. Marinate salmon for 30 minutes. Bake at 400°F (200°C) for 12-15 minutes until flaky.",
            "nutritional_info": "Excellent source of omega-3 fatty acids, high-quality protein, and B vitamins.",
            "cuisine_type": "Japanese fusion",
            "dietary_tags": ["high-protein", "dairy-free", "pescatarian"],
            "health_benefits": ["brain health", "heart health", "anti-inflammatory"]
        },
        {
            "name": "Chickpea and Vegetable Curry",
            "description": "A hearty plant-based curry loaded with protein-rich chickpeas and colorful vegetables in a fragrant sauce.",
            "ingredients": ["chickpeas", "sweet potatoes", "spinach", "tomatoes", "onion", "garlic", "ginger", "curry powder", "coconut milk", "vegetable broth"],
            "preparation": "Sauté onions, garlic, and ginger. Add curry powder, vegetables, chickpeas, and liquids. Simmer until vegetables are tender and flavors meld.",
            "nutritional_info": "High in plant protein, fiber, and antioxidants. Contains anti-inflammatory spices.",
            "cuisine_type": "Indian",
            "dietary_tags": ["vegan", "gluten-free", "dairy-free"],
            "health_benefits": ["gut health", "immune support", "plant-based protein"]
        },
        {
            "name": "Greek Yogurt Parfait",
            "description": "A protein-packed breakfast or snack featuring creamy Greek yogurt, fresh berries, and crunchy granola.",
            "ingredients": ["Greek yogurt", "mixed berries", "granola", "honey", "chia seeds", "sliced almonds"],
            "preparation": "Layer Greek yogurt with berries and granola. Drizzle with honey and sprinkle with chia seeds and almonds.",
            "nutritional_info": "High in protein, calcium, and antioxidants. Contains probiotics for gut health.",
            "cuisine_type": "Mediterranean-inspired",
            "dietary_tags": ["vegetarian", "high-protein", "probiotic-rich"],
            "health_benefits": ["gut health", "bone health", "muscle recovery"]
        },
        {
            "name": "Roasted Vegetable and Quinoa Salad",
            "description": "A satisfying salad with roasted seasonal vegetables, protein-rich quinoa, and a zesty vinaigrette.",
            "ingredients": ["quinoa", "bell peppers", "zucchini", "eggplant", "red onion", "cherry tomatoes", "olive oil", "balsamic vinegar", "fresh herbs", "feta cheese"],
            "preparation": "Roast vegetables until caramelized. Combine with cooked quinoa. Dress with olive oil and balsamic vinegar. Top with crumbled feta and fresh herbs.",
            "nutritional_info": "Balanced combination of complex carbs, plant protein, and healthy fats. Rich in vitamins and minerals.",
            "cuisine_type": "Mediterranean",
            "dietary_tags": ["vegetarian", "gluten-free", "high-fiber"],
            "health_benefits": ["digestive health", "sustained energy", "antioxidant-rich"]
        }
    ],
    "breakfast": [
        {
            "name": "Avocado Toast with Poached Egg",
            "description": "Whole grain toast topped with creamy avocado, a perfectly poached egg, and a sprinkle of microgreens. A balanced breakfast with healthy fats, protein, and complex carbs.",
            "ingredients": ["whole grain bread", "ripe avocado", "eggs", "microgreens", "lemon juice", "red pepper flakes", "sea salt", "black pepper"],
            "preparation": "Toast bread. Mash avocado with lemon juice, salt, and pepper. Spread on toast. Top with poached egg and microgreens.",
            "nutritional_info": "Rich in healthy fats, protein, and fiber. Contains essential vitamins and minerals.",
            "cuisine_type": "Modern",
            "dietary_tags": ["vegetarian", "high-protein", "heart-healthy"],
            "health_benefits": ["brain health", "sustained energy", "muscle recovery"]
        },
        {
            "name": "Berry and Chia Overnight Oats",
            "description": "A make-ahead breakfast featuring oats soaked in milk with chia seeds, topped with fresh berries and nuts. Perfect for busy mornings.",
            "ingredients": ["rolled oats", "milk or plant-based alternative", "chia seeds", "mixed berries", "maple syrup", "vanilla extract", "cinnamon", "chopped nuts"],
            "preparation": "Mix oats, milk, chia seeds, maple syrup, vanilla, and cinnamon. Refrigerate overnight. Top with berries and nuts before serving.",
            "nutritional_info": "High in fiber, omega-3 fatty acids, and antioxidants. Provides sustained energy release.",
            "cuisine_type": "Modern",
            "dietary_tags": ["vegetarian", "high-fiber", "make-ahead"],
            "health_benefits": ["heart health", "digestive health", "blood sugar regulation"]
        },
        {
            "name": "Spinach and Feta Omelette",
            "description": "A protein-packed omelette filled with nutrient-rich spinach and tangy feta cheese. A satisfying breakfast that will keep you full until lunch.",
            "ingredients": ["eggs", "fresh spinach", "feta cheese", "red onion", "olive oil", "fresh herbs", "salt", "pepper"],
            "preparation": "Whisk eggs. Sauté spinach and onion until wilted. Pour eggs over vegetables, cook until set. Sprinkle with feta and fold.",
            "nutritional_info": "Excellent source of protein, iron, calcium, and vitamins A and K.",
            "cuisine_type": "Mediterranean-inspired",
            "dietary_tags": ["vegetarian", "gluten-free", "keto-friendly", "high-protein"],
            "health_benefits": ["muscle maintenance", "bone health", "energy production"]
        },
        {
            "name": "Greek Yogurt Breakfast Bowl",
            "description": "Creamy Greek yogurt topped with fresh fruits, honey, and a variety of crunchy toppings. A quick, protein-rich breakfast option.",
            "ingredients": ["Greek yogurt", "mixed berries", "banana", "granola", "honey", "chia seeds", "flaxseeds", "sliced almonds"],
            "preparation": "Add Greek yogurt to a bowl. Top with fruits, granola, seeds, and nuts. Drizzle with honey.",
            "nutritional_info": "High in protein, calcium, and probiotics. Contains a mix of soluble and insoluble fiber.",
            "cuisine_type": "Mediterranean-inspired",
            "dietary_tags": ["vegetarian", "probiotic-rich", "high-protein"],
            "health_benefits": ["gut health", "immune support", "bone strength"]
        },
        {
            "name": "Whole Grain Breakfast Burrito",
            "description": "A satisfying breakfast burrito with scrambled eggs, black beans, vegetables, and avocado wrapped in a whole grain tortilla.",
            "ingredients": ["whole grain tortilla", "eggs", "black beans", "bell peppers", "onion", "avocado", "salsa", "cilantro", "lime juice"],
            "preparation": "Scramble eggs with sautéed vegetables. Warm black beans. Fill tortilla with eggs, beans, and sliced avocado. Top with salsa and cilantro.",
            "nutritional_info": "Balanced combination of protein, complex carbs, and healthy fats. Rich in fiber and essential nutrients.",
            "cuisine_type": "Mexican-inspired",
            "dietary_tags": ["high-protein", "high-fiber", "meal prep friendly"],
            "health_benefits": ["sustained energy", "muscle recovery", "digestive health"]
        }
    ],
    "vegetarian": [
        {
            "name": "Lentil and Vegetable Stew",
            "description": "A hearty plant-based stew packed with protein-rich lentils and seasonal vegetables. Perfect for a satisfying meat-free meal.",
            "ingredients": ["green or brown lentils", "carrots", "celery", "onion", "garlic", "tomatoes", "vegetable broth", "bay leaf", "thyme", "cumin"],
            "preparation": "Sauté vegetables until softened. Add lentils, tomatoes, broth, and seasonings. Simmer until lentils are tender and flavors meld.",
            "nutritional_info": "Excellent source of plant protein, fiber, iron, and B vitamins.",
            "cuisine_type": "Mediterranean",
            "dietary_tags": ["vegan", "gluten-free", "high-protein", "high-fiber"],
            "health_benefits": ["heart health", "blood sugar regulation", "digestive health"]
        },
        {
            "name": "Stuffed Bell Peppers with Quinoa",
            "description": "Colorful bell peppers stuffed with a flavorful mixture of quinoa, black beans, corn, and spices. A complete vegetarian meal in one package.",
            "ingredients": ["bell peppers", "quinoa", "black beans", "corn", "onion", "garlic", "tomatoes", "chili powder", "cumin", "cilantro", "lime juice"],
            "preparation": "Cook quinoa. Mix with beans, corn, and seasonings. Stuff into halved bell peppers. Bake until peppers are tender.",
            "nutritional_info": "Complete protein from quinoa and beans. Rich in fiber, vitamins C and A, and antioxidants.",
            "cuisine_type": "Mexican-inspired",
            "dietary_tags": ["vegetarian", "gluten-free", "high-protein"],
            "health_benefits": ["immune support", "digestive health", "sustained energy"]
        },
        {
            "name": "Chickpea and Spinach Curry",
            "description": "A fragrant curry featuring protein-rich chickpeas and iron-packed spinach in a creamy tomato-based sauce.",
            "ingredients": ["chickpeas", "spinach", "onion", "garlic", "ginger", "tomatoes", "coconut milk", "curry powder", "turmeric", "cumin", "coriander"],
            "preparation": "Sauté aromatics. Add spices, tomatoes, chickpeas, and coconut milk. Simmer until flavors meld. Stir in spinach until wilted.",
            "nutritional_info": "High in plant protein, iron, fiber, and anti-inflammatory compounds.",
            "cuisine_type": "Indian",
            "dietary_tags": ["vegan", "gluten-free", "dairy-free"],
            "health_benefits": ["iron-rich", "anti-inflammatory", "digestive health"]
        },
        {
            "name": "Mediterranean Vegetable Moussaka",
            "description": "A vegetarian version of the classic Greek dish featuring layers of eggplant, potatoes, lentils, and a creamy béchamel sauce.",
            "ingredients": ["eggplant", "potatoes", "lentils", "onion", "garlic", "tomatoes", "cinnamon", "nutmeg", "milk", "flour", "butter", "parmesan cheese"],
            "preparation": "Layer sliced eggplant and potatoes with lentil tomato sauce. Top with béchamel sauce. Bake until golden and bubbling.",
            "nutritional_info": "Good source of plant protein, fiber, and complex carbohydrates.",
            "cuisine_type": "Greek",
            "dietary_tags": ["vegetarian", "high-fiber"],
            "health_benefits": ["heart health", "sustained energy", "bone health"]
        },
        {
            "name": "Vegetable and Tofu Stir-Fry",
            "description": "A quick and colorful stir-fry featuring crisp vegetables and protein-rich tofu in a flavorful sauce.",
            "ingredients": ["firm tofu", "broccoli", "bell peppers", "carrots", "snow peas", "garlic", "ginger", "soy sauce", "sesame oil", "rice vinegar", "brown rice"],
            "preparation": "Press and cube tofu. Stir-fry with vegetables, garlic, and ginger. Add sauce ingredients. Serve over brown rice.",
            "nutritional_info": "Complete protein from tofu. Rich in fiber, vitamins, and minerals from colorful vegetables.",
            "cuisine_type": "Asian-inspired",
            "dietary_tags": ["vegetarian", "dairy-free", "high-protein"],
            "health_benefits": ["heart health", "hormone balance", "antioxidant-rich"]
        }
    ],
    "healthy": [
        {
            "name": "Grilled Salmon with Roasted Vegetables",
            "description": "Omega-3 rich salmon fillet served with a colorful medley of roasted seasonal vegetables. A complete, nutrient-dense meal.",
            "ingredients": ["salmon fillet", "zucchini", "bell peppers", "cherry tomatoes", "red onion", "olive oil", "lemon", "garlic", "fresh herbs", "salt", "pepper"],
            "preparation": "Season salmon with herbs, garlic, lemon. Toss vegetables with olive oil, salt, and pepper. Grill salmon and roast vegetables until done.",
            "nutritional_info": "Excellent source of omega-3 fatty acids, high-quality protein, and a wide range of vitamins and minerals.",
            "cuisine_type": "Mediterranean",
            "dietary_tags": ["gluten-free", "dairy-free", "high-protein", "pescatarian"],
            "health_benefits": ["heart health", "brain function", "anti-inflammatory"]
        },
        {
            "name": "Quinoa Buddha Bowl",
            "description": "A nourishing bowl featuring protein-rich quinoa, roasted and raw vegetables, avocado, and a tahini dressing. Perfect balance of macronutrients.",
            "ingredients": ["quinoa", "sweet potato", "kale", "chickpeas", "avocado", "red cabbage", "cucumber", "tahini", "lemon juice", "garlic", "maple syrup"],
            "preparation": "Cook quinoa. Roast sweet potatoes and chickpeas. Arrange all components in a bowl. Drizzle with tahini dressing.",
            "nutritional_info": "Complete protein from quinoa and chickpeas. Rich in fiber, healthy fats, and a wide spectrum of micronutrients.",
            "cuisine_type": "Modern",
            "dietary_tags": ["vegan", "gluten-free", "high-fiber"],
            "health_benefits": ["digestive health", "sustained energy", "immune support"]
        },
        {
            "name": "Turkey and Vegetable Lettuce Wraps",
            "description": "Lean ground turkey and vegetables wrapped in crisp lettuce leaves. A light yet satisfying meal that's low in carbs but high in flavor.",
            "ingredients": ["lean ground turkey", "bell peppers", "carrots", "water chestnuts", "garlic", "ginger", "green onions", "soy sauce", "hoisin sauce", "lettuce leaves"],
            "preparation": "Brown turkey. Add vegetables and seasonings. Cook until vegetables are tender. Serve in lettuce leaves.",
            "nutritional_info": "Lean protein with minimal carbohydrates. Rich in vitamins, minerals, and water content.",
            "cuisine_type": "Asian-inspired",
            "dietary_tags": ["dairy-free", "low-carb", "high-protein"],
            "health_benefits": ["weight management", "muscle maintenance", "hydration"]
        },
        {
            "name": "Mediterranean Lentil Salad",
            "description": "A protein-packed salad featuring lentils, fresh vegetables, feta cheese, and a lemon-herb dressing. Perfect for meal prep.",
            "ingredients": ["green or brown lentils", "cucumber", "cherry tomatoes", "red onion", "bell pepper", "feta cheese", "parsley", "mint", "olive oil", "lemon juice"],
            "preparation": "Cook lentils until tender. Combine with chopped vegetables, herbs, and feta. Dress with olive oil and lemon juice.",
            "nutritional_info": "High in plant protein, fiber, and essential minerals like iron and folate.",
            "cuisine_type": "Mediterranean",
            "dietary_tags": ["vegetarian", "gluten-free", "high-fiber"],
            "health_benefits": ["heart health", "digestive health", "sustained energy"]
        },
        {
            "name": "Baked Cod with Herb Crust",
            "description": "Flaky white fish topped with a flavorful herb crust, served with steamed vegetables. A light, protein-rich meal.",
            "ingredients": ["cod fillets", "whole grain breadcrumbs", "parsley", "dill", "lemon zest", "olive oil", "dijon mustard", "garlic", "broccoli", "carrots"],
            "preparation": "Mix herbs, breadcrumbs, and lemon zest. Brush fish with mustard and olive oil. Top with herb mixture. Bake until fish flakes easily.",
            "nutritional_info": "Lean protein with omega-3 fatty acids. Low in calories but high in nutrients.",
            "cuisine_type": "European",
            "dietary_tags": ["dairy-free", "high-protein", "pescatarian"],
            "health_benefits": ["heart health", "brain function", "weight management"]
        }
    ],
    "quick": [
        {
            "name": "15-Minute Chickpea and Spinach Curry",
            "description": "A speedy curry using canned chickpeas and fresh spinach. Ready in just 15 minutes but packed with flavor and nutrition.",
            "ingredients": ["canned chickpeas", "spinach", "onion", "garlic", "ginger", "curry powder", "coconut milk", "tomato paste", "lime juice"],
            "preparation": "Sauté onion, garlic, and ginger. Add curry powder, chickpeas, coconut milk, and tomato paste. Simmer briefly. Stir in spinach until wilted.",
            "nutritional_info": "Plant-based protein and iron from chickpeas and spinach. Rich in fiber and anti-inflammatory compounds.",
            "cuisine_type": "Indian-inspired",
            "dietary_tags": ["vegan", "gluten-free", "one-pot"],
            "health_benefits": ["plant protein", "iron-rich", "quick energy"]
        },
        {
            "name": "Tuna and White Bean Salad",
            "description": "A no-cook protein-packed salad combining canned tuna, white beans, and fresh vegetables. Perfect for a quick lunch or dinner.",
            "ingredients": ["canned tuna", "cannellini beans", "red onion", "cherry tomatoes", "arugula", "lemon juice", "olive oil", "fresh herbs", "capers"],
            "preparation": "Combine all ingredients in a bowl. Dress with olive oil and lemon juice. Season to taste.",
            "nutritional_info": "High in protein from both tuna and beans. Good source of fiber and omega-3 fatty acids.",
            "cuisine_type": "Mediterranean",
            "dietary_tags": ["dairy-free", "gluten-free", "high-protein"],
            "health_benefits": ["heart health", "muscle maintenance", "brain function"]
        },
        {
            "name": "Egg and Vegetable Fried Rice",
            "description": "A quick stir-fry using leftover rice, eggs, and whatever vegetables you have on hand. A complete meal in minutes.",
            "ingredients": ["cooked rice", "eggs", "mixed vegetables", "garlic", "ginger", "green onions", "soy sauce", "sesame oil"],
            "preparation": "Scramble eggs. Stir-fry vegetables. Add rice, soy sauce, and sesame oil. Mix well and serve.",
            "nutritional_info": "Balanced combination of protein, carbs, and vegetables. Quick source of energy.",
            "cuisine_type": "Asian-inspired",
            "dietary_tags": ["vegetarian", "dairy-free", "quick meal"],
            "health_benefits": ["energy boost", "uses leftovers", "balanced nutrition"]
        },
        {
            "name": "Mediterranean Wrap",
            "description": "A quick wrap filled with hummus, fresh vegetables, and feta cheese. No cooking required and ready in minutes.",
            "ingredients": ["whole grain wrap", "hummus", "cucumber", "tomato", "red onion", "feta cheese", "kalamata olives", "lettuce"],
            "preparation": "Spread hummus on wrap. Layer with vegetables, feta, and olives. Roll up and enjoy.",
            "nutritional_info": "Plant protein from hummus. Rich in fiber, vitamins, and minerals from fresh vegetables.",
            "cuisine_type": "Mediterranean",
            "dietary_tags": ["vegetarian", "no-cook", "high-fiber"],
            "health_benefits": ["heart health", "quick energy", "digestive health"]
        },
        {
            "name": "Microwave Sweet Potato with Toppings",
            "description": "A nutritious meal centered around a microwave-cooked sweet potato with various healthy toppings. Fast, filling, and nutritious.",
            "ingredients": ["sweet potato", "black beans", "Greek yogurt", "avocado", "salsa", "green onions", "cilantro", "lime juice"],
            "preparation": "Pierce sweet potato and microwave until tender. Split open and top with remaining ingredients.",
            "nutritional_info": "Rich in complex carbs, fiber, and vitamins A and C. Protein from beans and Greek yogurt.",
            "cuisine_type": "Fusion",
            "dietary_tags": ["vegetarian", "gluten-free", "minimal cooking"],
            "health_benefits": ["gut health", "sustained energy", "immune support"]
        }
    ]
}

def generate_mock_llm_response(
    query: str,
    limit: int = 5,
    user_preferences: Optional[Dict[str, Any]] = None,
    available_foods: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Generate a mock LLM response with personalized food recommendations.
    
    Args:
        query: The user's food query
        limit: Maximum number of recommendations to return
        user_preferences: Optional user preferences to customize recommendations
        available_foods: Optional list of available foods to reference
        
    Returns:
        List of food recommendation dictionaries
    """
    # Create a base set of recommendations that look like they came from an LLM
    mock_recommendations = [
        {
            "name": "Protein-Packed Buddha Bowl",
            "description": "A nutrient-dense bowl with quinoa, roasted chickpeas, avocado, and a variety of colorful vegetables. This balanced meal provides sustained energy and supports your fitness goals.",
            "ingredients": ["quinoa", "chickpeas", "avocado", "kale", "sweet potato", "red cabbage", "tahini", "lemon juice", "olive oil", "sesame seeds"],
            "preparation": "Cook quinoa and roast chickpeas with spices. Arrange all ingredients in a bowl and drizzle with tahini-lemon dressing.",
            "nutritional_info": {
                "calories": 450,
                "protein": 15,
                "carbs": 55,
                "fat": 20,
                "fiber": 12
            },
            "cuisine_type": "Fusion",
            "dietary_tags": ["vegetarian", "gluten-free", "high-protein"],
            "health_benefits": ["muscle recovery", "digestive health", "immune support"]
        },
        {
            "name": "Wild-Caught Salmon with Roasted Vegetables",
            "description": "Omega-3 rich salmon fillet served with a colorful medley of seasonal roasted vegetables. This dish supports brain health, reduces inflammation, and provides high-quality protein.",
            "ingredients": ["wild salmon fillet", "broccoli", "bell peppers", "zucchini", "red onion", "garlic", "olive oil", "lemon", "dill", "thyme"],
            "preparation": "Season salmon with herbs and lemon. Roast vegetables until caramelized. Bake salmon until just cooked through.",
            "nutritional_info": {
                "calories": 380,
                "protein": 28,
                "carbs": 18,
                "fat": 22,
                "fiber": 6
            },
            "cuisine_type": "Mediterranean",
            "dietary_tags": ["gluten-free", "dairy-free", "pescatarian"],
            "health_benefits": ["brain health", "anti-inflammatory", "heart health"]
        },
        {
            "name": "Lentil and Vegetable Soup",
            "description": "A hearty, fiber-rich soup packed with plant-based protein from lentils and a variety of vegetables. Perfect for supporting digestive health and providing sustained energy.",
            "ingredients": ["green lentils", "carrots", "celery", "onion", "garlic", "tomatoes", "spinach", "vegetable broth", "cumin", "thyme"],
            "preparation": "Sauté vegetables, add lentils and broth. Simmer until lentils are tender. Season with herbs and spices.",
            "nutritional_info": {
                "calories": 320,
                "protein": 18,
                "carbs": 45,
                "fat": 6,
                "fiber": 15
            },
            "cuisine_type": "Mediterranean",
            "dietary_tags": ["vegan", "gluten-free", "high-fiber"],
            "health_benefits": ["digestive health", "heart health", "blood sugar regulation"]
        },
        {
            "name": "Greek Yogurt Parfait with Berries and Nuts",
            "description": "A protein-rich breakfast or snack featuring probiotic Greek yogurt, antioxidant-packed berries, and crunchy nuts for healthy fats. Supports gut health and provides balanced nutrition.",
            "ingredients": ["Greek yogurt", "mixed berries", "almonds", "walnuts", "chia seeds", "honey", "cinnamon"],
            "preparation": "Layer Greek yogurt with berries, nuts, and seeds. Drizzle with honey and sprinkle with cinnamon.",
            "nutritional_info": {
                "calories": 280,
                "protein": 20,
                "carbs": 25,
                "fat": 12,
                "fiber": 8
            },
            "cuisine_type": "Mediterranean-inspired",
            "dietary_tags": ["vegetarian", "gluten-free", "probiotic-rich"],
            "health_benefits": ["gut health", "muscle recovery", "antioxidant-rich"]
        },
        {
            "name": "Turmeric Chicken with Cauliflower Rice",
            "description": "Anti-inflammatory turmeric-spiced chicken served with low-carb cauliflower rice. This dish supports recovery, provides lean protein, and offers a nutrient-dense alternative to traditional rice dishes.",
            "ingredients": ["chicken breast", "turmeric", "ginger", "garlic", "cauliflower", "coconut oil", "cilantro", "lime", "black pepper"],
            "preparation": "Season chicken with turmeric, ginger, and garlic. Grill until cooked through. Pulse cauliflower in food processor and sauté until tender.",
            "nutritional_info": {
                "calories": 350,
                "protein": 35,
                "carbs": 12,
                "fat": 15,
                "fiber": 5
            },
            "cuisine_type": "Asian-fusion",
            "dietary_tags": ["gluten-free", "dairy-free", "low-carb"],
            "health_benefits": ["anti-inflammatory", "muscle building", "weight management"]
        },
        {
            "name": "Vegetable and Bean Enchiladas",
            "description": "Fiber-rich bean and vegetable enchiladas with a homemade sauce. This plant-based dish provides complete protein, supports digestive health, and offers a variety of phytonutrients.",
            "ingredients": ["corn tortillas", "black beans", "pinto beans", "bell peppers", "zucchini", "onion", "tomatoes", "chili powder", "cumin", "avocado"],
            "preparation": "Sauté vegetables, combine with beans and spices. Roll in tortillas, top with sauce, and bake until bubbly.",
            "nutritional_info": {
                "calories": 400,
                "protein": 16,
                "carbs": 60,
                "fat": 10,
                "fiber": 14
            },
            "cuisine_type": "Mexican",
            "dietary_tags": ["vegetarian", "dairy-free", "high-fiber"],
            "health_benefits": ["digestive health", "sustained energy", "heart health"]
        },
        {
            "name": "Baked Cod with Herb Crust and Roasted Sweet Potatoes",
            "description": "Lean white fish with a flavorful herb crust served with vitamin-rich roasted sweet potatoes. This balanced meal supports muscle maintenance while providing complex carbohydrates for energy.",
            "ingredients": ["cod fillets", "whole grain breadcrumbs", "parsley", "thyme", "lemon zest", "sweet potatoes", "olive oil", "garlic", "paprika"],
            "preparation": "Coat cod with herb-breadcrumb mixture and bake. Roast sweet potato cubes with garlic and paprika.",
            "nutritional_info": {
                "calories": 360,
                "protein": 30,
                "carbs": 35,
                "fat": 8,
                "fiber": 6
            },
            "cuisine_type": "Mediterranean",
            "dietary_tags": ["dairy-free", "high-protein", "pescatarian"],
            "health_benefits": ["muscle maintenance", "immune support", "eye health"]
        }
    ]
    
    # Personalize based on query keywords
    query_lower = query.lower()
    
    # Filter recommendations based on query keywords
    filtered_recommendations = []
    
    # Check for dietary preferences in query
    is_vegetarian = any(word in query_lower for word in ["vegetarian", "vegan", "plant", "meatless"])
    is_protein_focused = any(word in query_lower for word in ["protein", "muscle", "workout", "gym", "fitness"])
    is_low_carb = any(word in query_lower for word in ["low carb", "keto", "low-carb", "carb-free"])
    is_breakfast = any(word in query_lower for word in ["breakfast", "morning", "brunch"])
    
    # Filter based on preferences
    for rec in mock_recommendations:
        # Skip non-vegetarian options if vegetarian is requested
        if is_vegetarian and not any(tag in rec["dietary_tags"] for tag in ["vegetarian", "vegan"]):
            continue
            
        # Prioritize high-protein options if protein-focused
        if is_protein_focused and "high-protein" not in rec["dietary_tags"]:
            # Still include some protein options but with lower priority
            if rec["nutritional_info"]["protein"] > 20:
                filtered_recommendations.append(rec)
            continue
            
        # Filter for low-carb options
        if is_low_carb and rec["nutritional_info"]["carbs"] > 20:
            continue
            
        # Filter for breakfast options
        if is_breakfast and rec["name"] != "Greek Yogurt Parfait with Berries and Nuts":
            # Add a breakfast tag to make it look more relevant
            if "Greek Yogurt" in rec["name"] or "Egg" in rec["name"]:
                rec["dietary_tags"].append("breakfast")
                filtered_recommendations.append(rec)
            continue
            
        # Add recommendation if it passed all filters
        filtered_recommendations.append(rec)
    
    # If no recommendations match the filters, return a subset of the original recommendations
    if not filtered_recommendations:
        filtered_recommendations = mock_recommendations
    
    # If available foods are provided, try to match some recommendations with available foods
    if available_foods and len(available_foods) > 0:
        for i, rec in enumerate(filtered_recommendations):
            if i < len(available_foods):
                # Add food_id from available foods
                rec["food_id"] = available_foods[i].get("id", "")
    
    # Add a conversation element to make it look more like an LLM response
    conversation_elements = [
        f"Based on your query about '{query}', I've selected nutritionally balanced options that will support your health goals.",
        f"Here are some personalized recommendations based on your interest in '{query}'.",
        f"I've analyzed your request for '{query}' and selected these options based on nutritional value and flavor profile.",
        f"For your query about '{query}', I've chosen these balanced meals that provide essential nutrients and satisfy your preferences."
    ]
    
    # Return limited number of recommendations
    return filtered_recommendations[:limit], conversation_elements[hash(query) % len(conversation_elements)]

async def get_dr_foodlove_recommendations(
    query: str,
    user_preferences: Optional[Dict[str, Any]] = None,
    limit: int = 5,
    food_image_path: Optional[str] = None,
    detailed_response: bool = False,
    available_foods: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Get personalized food recommendations from Dr. Foodlove AI using mock LLM responses.
    
    Args:
        query: The user's food query or request
        user_preferences: Optional user preferences to customize recommendations
        limit: Maximum number of recommendations to return
        food_image_path: Optional path to a food image for analysis
        detailed_response: Whether to include detailed nutritional information
        available_foods: Optional list of available foods in the database to constrain recommendations
        
    Returns:
        Dictionary containing AI recommendations and metadata
    """
    # Log the input parameters for debugging
    logger.info(f"Dr.Foodlove API called with query: '{query}'")
    logger.info(f"User preferences provided: {user_preferences is not None}")
    logger.info(f"Available foods provided: {available_foods is not None}")
    logger.info(f"Limit: {limit}, Detailed response: {detailed_response}")
    
    # Generate mock LLM response
    recommendations, conversation = generate_mock_llm_response(
        query=query,
        limit=limit,
        user_preferences=user_preferences,
        available_foods=available_foods
    )
    
    # Generate response
    response = {
        "success": True,
        "query": query,
        "provider": "Dr. Foodlove AI",
        "recommendations": recommendations,
        "user_preferences_applied": user_preferences is not None,
        "available_foods_used": available_foods is not None,
        "conversation": conversation
    }
    
    # Add health insights if detailed response is requested
    if detailed_response:
        response["health_insights"] = generate_health_insights(
            query, 
            recommendations,
            user_preferences
        )
    
    logger.info(f"Successfully processed {len(recommendations)} mock LLM recommendations")
    return response

def generate_health_insights(
    query: str, 
    recommendations: List[Dict[str, Any]],
    user_preferences: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate health insights based on the recommendations and user preferences.
    
    Args:
        query: The user's original query
        recommendations: List of food recommendations
        user_preferences: Optional user preferences
        
    Returns:
        Dictionary containing health insights
    """
    # Extract food types from recommendations
    food_types = []
    nutrients = {"protein": 0, "fiber": 0, "vitamins": []}
    
    for rec in recommendations:
        # Extract cuisine type
        if rec.get("cuisine_type"):
            food_types.append(rec.get("cuisine_type"))
        
        # Extract nutrients from description or nutritional info
        if rec.get("nutritional_info"):
            if isinstance(rec["nutritional_info"], dict):
                if "protein" in rec["nutritional_info"]:
                    nutrients["protein"] += 1
                if "fiber" in rec["nutritional_info"]:
                    nutrients["fiber"] += 1
        
        # Check description for nutrient mentions
        description = rec.get("description", "").lower()
        if "protein" in description:
            nutrients["protein"] += 1
        if "fiber" in description:
            nutrients["fiber"] += 1
        if "vitamin" in description:
            for vitamin in ["a", "b", "c", "d", "e"]:
                if f"vitamin {vitamin}" in description:
                    nutrients["vitamins"].append(vitamin.upper())
    
    # Generate insights
    insights = {
        "variety": len(set(food_types)),
        "nutrient_focus": [],
        "balance_score": min(5, len(set(food_types)) + (nutrients["protein"] > 0) + (nutrients["fiber"] > 0)),
        "recommendations": []
    }
    
    # Add nutrient focus
    if nutrients["protein"] >= 2:
        insights["nutrient_focus"].append("protein")
    if nutrients["fiber"] >= 2:
        insights["nutrient_focus"].append("fiber")
    if len(set(nutrients["vitamins"])) >= 2:
        insights["nutrient_focus"].append("vitamins")
    
    # Add general recommendations
    if insights["balance_score"] < 3:
        insights["recommendations"].append("Consider adding more variety to your meals")
    if "protein" not in insights["nutrient_focus"]:
        insights["recommendations"].append("You might want to include more protein-rich foods")
    if "fiber" not in insights["nutrient_focus"]:
        insights["recommendations"].append("Consider adding more fiber-rich foods for digestive health")
    
    return insights 