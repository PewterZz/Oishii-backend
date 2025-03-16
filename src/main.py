from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .api.v1.api import router as api_router
from .core.supabase import supabase
import os
from dotenv import load_dotenv
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import asyncio
from .core.scheduler import run_scheduled_tasks
from .core.datastax import initialize_datastax

# Load environment variables
load_dotenv()

# Application settings
APP_NAME = os.getenv("APP_NAME", "Oishii API")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to Supabase and start scheduler
    print(f"Starting up: Connected to Supabase in {ENVIRONMENT} environment")
    
    # Initialize DataStax
    await initialize_datastax()
    print("Initialized DataStax connection and tables")
    
    # Start scheduler in a background task
    if ENVIRONMENT == "production":
        task = asyncio.create_task(run_scheduled_tasks())
        print("Started scheduler for background tasks")
    
    yield
    
    # Shutdown: Clean up resources
    print("Shutting down")
    
    # Cancel scheduler task if it exists
    if ENVIRONMENT == "production" and "task" in locals():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            print("Scheduler task cancelled")

app = FastAPI(
    title=APP_NAME,
    description="""
    API for the Oishii food swapping app.
    
    ## Authentication
    
    To authenticate with the API, you can:
    
    1. Use the `/api/v1/users/swagger-token` endpoint to get a token specifically formatted for Swagger UI.
    2. Copy the token and click the "Authorize" button at the top of this page.
    3. Paste the token in the value field (no need to add "Bearer" prefix).
    4. Click "Authorize" and close the dialog.
    
    You can also use the `/api/v1/users/quick-token` endpoint to get a token in JSON format.
    
    ### Troubleshooting Authentication
    
    If you're experiencing authentication issues:
    
    1. Make sure you've clicked the "Authorize" button at the top of the page and entered your token.
    2. Verify your token is valid by using the `/api/v1/users/check-auth` endpoint.
    3. Tokens expire after a certain period (default: 30 minutes). Get a new token if needed.
    4. Check that you're not including the "Bearer" prefix when entering the token in Swagger UI.
    5. If you're using the API programmatically, include the token in the Authorization header as `Bearer your-token`.
    """,
    version="1.0.0",
    debug=DEBUG,
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
        "defaultModelsExpandDepth": -1,
        "docExpansion": "none",
    }
)

# Configure CORS
# Default origins for development
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    FRONTEND_URL,  # Include the frontend URL from environment
]

# Add production origins if in production environment
if ENVIRONMENT == "production":
    production_origins = [
        "https://oishii.app",
        "https://www.oishii.app",
        "https://oishii-backend.fly.dev",
        "https://oishii-frontend.fly.dev",
    ]
    origins.extend(production_origins)

print(f"CORS origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter the token without the 'Bearer' prefix"
        }
    }
    
    # Instead of applying security globally, we need to apply it to specific paths
    # that require authentication
    if "paths" in openapi_schema:
        for path in openapi_schema["paths"]:
            # Skip authentication endpoints and public endpoints
            if (path.endswith("/login") or 
                path.endswith("/register") or 
                path.endswith("/verify") or 
                path.endswith("/callback") or
                path.endswith("/dev/token") or
                path == "/" or
                path == "/health" or
                path.endswith("/foods") and "get" in openapi_schema["paths"][path]):
                # These endpoints don't require authentication
                continue
            
            # Apply security to all operations in this path
            for method in openapi_schema["paths"][path]:
                if method != "parameters":  # Skip the parameters field
                    openapi_schema["paths"][path][method]["security"] = [{"bearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/")
async def root():
    return {"message": f"Welcome to the {APP_NAME}", "environment": ENVIRONMENT}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": ENVIRONMENT}

# Add exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_messages = []
    
    for error in errors:
        # Check if it's a UUID parsing error
        if error.get("type") == "uuid_parsing":
            loc = error.get("loc", [])
            if len(loc) >= 2 and loc[0] == "path" and loc[1] == "food_id":
                input_value = error.get("input", "")
                return JSONResponse(
                    status_code=422,
                    content={
                        "detail": f"Invalid UUID format for food_id: '{input_value}'. Please provide a valid UUID.",
                        "hint": "If you're trying to get a list of foods, use the /api/v1/foods endpoint instead."
                    }
                )
        
        # Add other error messages
        error_messages.append(error)
    
    return JSONResponse(
        status_code=422,
        content={"detail": error_messages}
    )
