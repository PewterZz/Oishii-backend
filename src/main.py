from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .api.v1.api import router as api_router
from .core.supabase import supabase
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Application settings
APP_NAME = os.getenv("APP_NAME", "Oishii API")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to Supabase
    print(f"Starting up: Connected to Supabase in {ENVIRONMENT} environment")
    yield
    # Shutdown: Clean up resources
    print("Shutting down")

app = FastAPI(
    title=APP_NAME,
    description="API for the Oishii food swapping app",
    version="1.0.0",
    debug=DEBUG,
    lifespan=lifespan
)

# Configure CORS
origins = ["*"]  # In production, replace with specific origins
if ENVIRONMENT == "production":
    origins = [
        "https://oishii.app",
        "https://www.oishii.app",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": f"Welcome to the {APP_NAME}", "environment": ENVIRONMENT}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": ENVIRONMENT}
