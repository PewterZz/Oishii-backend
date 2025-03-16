# Dr. Foodlove AI Integration for Oishii

This document explains how to set up and use the Dr. Foodlove AI integration for personalized food recommendations in the Oishii application.

## Overview

Dr. Foodlove is an AI nutritionist and food expert that provides personalized food recommendations based on user preferences, dietary restrictions, and health goals. The integration uses DataStax Langflow as the underlying AI engine and enhances it with nutrition-focused prompting and health insights.

## Features

- **Personalized Recommendations**: Get food recommendations tailored to individual preferences, dietary restrictions, and health goals
- **Health Insights**: Receive nutritional analysis and health-focused suggestions
- **Image Analysis**: Upload food images for analysis and related recommendations
- **Detailed Nutrition Information**: Get comprehensive nutritional information for each recommendation
- **Multiple Cuisine Types**: Explore diverse food options from various cuisines

## Configuration

### Environment Variables

The Dr. Foodlove integration uses the same environment variables as the DataStax Langflow integration:

```
# DataStax Langflow Configuration
DATASTAX_LANGFLOW_API_URL=https://api.langflow.astra.datastax.com
DATASTAX_LANGFLOW_ID=f97d1e16-3dd8-4355-99fa-e8f1b98563ae
DATASTAX_FLOW_ID=567ad106-a9f3-4e30-b909-628e89186549
DATASTAX_APPLICATION_TOKEN=your-application-token
DATASTAX_ENDPOINT=your-endpoint-name
```

Replace `your-application-token` with your actual DataStax Application token.

## API Endpoints

### Dr. Foodlove Recommendations

```
POST /api/v1/recommendations/dr-foodlove
```

Request body:

```json
{
  "query": "healthy breakfast options for weight loss",
  "include_user_preferences": true,
  "limit": 5,
  "detailed_response": true,
  "custom_preferences": {
    "dietary_restrictions": ["gluten-free"],
    "health_goals": ["weight loss", "increased energy"],
    "meal_type": "breakfast"
  }
}
```

Response:

```json
{
  "success": true,
  "query": "healthy breakfast options for weight loss",
  "provider": "Dr. Foodlove AI",
  "recommendations": [
    {
      "name": "Greek Yogurt Parfait with Berries and Nuts",
      "description": "A protein-rich breakfast parfait that's satisfying and supports weight loss.",
      "ingredients": ["Greek yogurt", "mixed berries", "almonds", "honey", "cinnamon"],
      "preparation": "Layer Greek yogurt with berries and top with a sprinkle of nuts and a drizzle of honey.",
      "nutritional_info": {
        "calories": 280,
        "protein": 18,
        "carbs": 30,
        "fat": 12,
        "fiber": 6
      },
      "cuisine_type": "Mediterranean",
      "dietary_tags": ["gluten-free", "vegetarian", "high-protein"],
      "health_benefits": ["Supports weight loss", "Provides sustained energy", "Rich in antioxidants"]
    },
    // More recommendations...
  ],
  "user_preferences_applied": true,
  "health_insights": {
    "variety": 3,
    "nutrient_focus": ["protein", "fiber"],
    "balance_score": 4,
    "recommendations": [
      "These options are well-balanced for weight loss with adequate protein",
      "Consider adding more fiber-rich foods for digestive health"
    ]
  }
}
```

### Dr. Foodlove Image Analysis

```
POST /api/v1/recommendations/dr-foodlove/image
```

This endpoint accepts multipart form data with the following fields:

- `query`: The food query or question (required)
- `food_image`: The image file to analyze (required)
- `include_user_preferences`: Whether to include user preferences (boolean)
- `limit`: Maximum number of recommendations (integer)
- `detailed_response`: Whether to include detailed health insights (boolean)
- `custom_preferences`: JSON string of custom preferences (optional)

Example curl request:

```bash
curl -X POST "http://localhost:8000/api/v1/recommendations/dr-foodlove/image" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "query=what is this dish and what are similar healthy alternatives" \
  -F "food_image=@/path/to/food_image.jpg" \
  -F "include_user_preferences=true" \
  -F "detailed_response=true" \
  -F "custom_preferences={\"dietary_restrictions\":[\"gluten-free\"]}"
```

## Testing the Integration

You can test the Dr. Foodlove integration using the provided command-line utility:

```bash
# Activate your virtual environment
source venv/bin/activate

# Basic usage
python -m src.utils.dr_foodlove_cli --query "healthy breakfast options" --token YOUR_TOKEN

# With user preferences and health goals
python -m src.utils.dr_foodlove_cli --query "dinner ideas" --preferences --health-goals "weight loss,muscle gain" --detailed

# With image analysis
python -m src.utils.dr_foodlove_cli --query "what is this dish and suggest alternatives" --image path/to/food_image.jpg

# Save response to file
python -m src.utils.dr_foodlove_cli --query "lunch ideas for kids" --output response.json
```

Options:
- `--query`: The food query to send to Dr. Foodlove (required)
- `--token`: Your DataStax Application Token (overrides env variable)
- `--limit`: Maximum number of recommendations (default: 5)
- `--preferences`: Include sample user preferences
- `--detailed`: Include detailed health insights
- `--image`: Path to a food image to analyze
- `--output`: Path to save the response as JSON
- `--health-goals`: Comma-separated list of health goals

## User Preferences

Dr. Foodlove can consider various user preferences to personalize recommendations:

- **Dietary Restrictions**: vegetarian, vegan, gluten-free, dairy-free, etc.
- **Allergies**: nuts, shellfish, eggs, soy, etc.
- **Cuisine Preferences**: Italian, Japanese, Mexican, Indian, etc.
- **Health Goals**: weight loss, muscle gain, heart health, diabetes management, etc.
- **Meal Types**: breakfast, lunch, dinner, snack, dessert
- **Cooking Skill Level**: beginner, intermediate, advanced
- **Time Constraints**: quick meals, meal prep, etc.

## Health Insights

When `detailed_response` is set to `true`, Dr. Foodlove provides health insights that include:

- **Variety Score**: A measure of the diversity of food types recommended
- **Nutrient Focus**: Key nutrients emphasized in the recommendations
- **Balance Score**: A rating of the overall nutritional balance (1-5)
- **Recommendations**: Specific health-focused suggestions

## Troubleshooting

If you encounter issues with the Dr. Foodlove integration:

1. Verify that your DataStax Application token is correct and has the necessary permissions
2. Check that the Langflow ID and Flow ID are correctly configured
3. Ensure that the DataStax Astra service is running and accessible
4. Check the application logs for detailed error messages
5. Try using the CLI utility with the `--token` parameter to test your token directly

For more information, refer to the [DataStax Langflow documentation](https://docs.datastax.com/en/astra-streaming/docs/astra-streaming-learning/langflow.html). 