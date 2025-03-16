# DataStax Langflow Integration for Dr. Foodlove

This document explains how to set up and use the DataStax Langflow integration for AI-powered food recommendations in the Dr. Foodlove application.

## Overview

The integration uses DataStax Langflow to provide AI-powered food recommendations based on user queries and preferences. The Langflow service connects to a pre-configured flow in DataStax Astra that processes natural language queries and returns relevant food recommendations.

## Configuration

### Environment Variables

Add the following environment variables to your `.env` file:

```
# DataStax Langflow Configuration
DATASTAX_LANGFLOW_API_URL=https://api.langflow.astra.datastax.com
DATASTAX_LANGFLOW_ID=f97d1e16-3dd8-4355-99fa-e8f1b98563ae
DATASTAX_FLOW_ID=567ad106-a9f3-4e30-b909-628e89186549
DATASTAX_APPLICATION_TOKEN=your-application-token
DATASTAX_ENDPOINT=your-endpoint-name
```

Replace `your-application-token` with your actual DataStax Application token.

### Dependencies

The integration requires the following Python packages, which are included in the `requirements.txt` file:

- `langflow>=1.0.0,<2.0.0` (compatible with latest versions)
- `requests==2.31.0`

## API Endpoints

### AI Food Recommendations

```
POST /api/v1/recommendations/ai-recommendations
```

Request body:

```json
{
  "query": "healthy breakfast options",
  "include_user_preferences": true,
  "limit": 5,
  "tweaks": {
    "Agent-2vwsZ": {},
    "ChatInput-5yMvY": {},
    "ChatOutput-5gdX7": {},
    "URL-Avwp7": {},
    "CalculatorComponent-Hh47N": {}
  }
}
```

Response:

```json
{
  "success": true,
  "query": "healthy breakfast options",
  "recommendations": [
    {
      "name": "Overnight Oats with Berries",
      "description": "A nutritious breakfast option made with rolled oats, yogurt, and fresh berries.",
      "ingredients": ["rolled oats", "yogurt", "berries", "honey", "chia seeds"],
      "preparation": "Mix ingredients and refrigerate overnight.",
      "nutritional_info": {
        "calories": 350,
        "protein": 15,
        "carbs": 45,
        "fat": 10
      },
      "cuisine_type": "International",
      "dietary_tags": ["vegetarian", "high-fiber"]
    },
    // More recommendations...
  ],
  "user_preferences_applied": true
}
```

## Testing the Integration

You can test the DataStax Langflow integration using the provided command-line utility:

```bash
# Activate your virtual environment
source venv/bin/activate

# Basic usage
python -m src.utils.langflow_cli --query "healthy breakfast options" --token YOUR_TOKEN

# With user preferences
python -m src.utils.langflow_cli --query "healthy breakfast options" --token YOUR_TOKEN --preferences

# With file upload (e.g., food image)
python -m src.utils.langflow_cli --query "what is this dish?" --file path/to/food_image.jpg --components ComponentID1,ComponentID2

# Save response to file
python -m src.utils.langflow_cli --query "dinner ideas" --output response.json
```

Options:
- `--query`: The food query to send to the AI (required)
- `--token`: Your DataStax Application Token (overrides env variable)
- `--limit`: Maximum number of recommendations (default: 5)
- `--preferences`: Include sample user preferences
- `--raw`: Use raw Langflow API instead of food recommendations
- `--file`: Path to a file to upload (e.g., food image)
- `--components`: Comma-separated list of component IDs to upload the file to
- `--output`: Path to save the response as JSON

## Flow Configuration

The DataStax Langflow integration uses a pre-configured flow with the following components:

- Agent: Processes the user query and generates food recommendations
- ChatInput: Accepts the user's query
- ChatOutput: Formats the response
- URL: Allows fetching additional information from external sources
- CalculatorComponent: Performs calculations for nutritional information

You can customize the flow by modifying the `tweaks` parameter in the API request or by updating the default tweaks in the `langflow_service.py` file.

## Response Processing

The integration includes a response processor that handles various formats of AI responses and converts them into a standardized structure. This ensures that regardless of how the AI formats its output, your application will receive consistently structured data.

The processor handles:
- JSON responses
- Text-based responses
- List-based responses
- Dictionary-based responses

Each recommendation is standardized to include:
- name
- description
- ingredients
- preparation
- nutritional_info
- cuisine_type
- dietary_tags
- confidence_score

## Troubleshooting

If you encounter issues with the DataStax Langflow integration:

1. Verify that your DataStax Application token is correct and has the necessary permissions
2. Check that the Langflow ID and Flow ID are correctly configured
3. Ensure that the DataStax Astra service is running and accessible
4. Check the application logs for detailed error messages
5. If you're having issues with the langflow package, try using a different version by modifying the requirements.txt file

For more information, refer to the [DataStax Langflow documentation](https://docs.datastax.com/en/astra-streaming/docs/astra-streaming-learning/langflow.html). 