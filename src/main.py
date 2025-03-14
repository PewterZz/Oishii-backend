from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import get_settings
from .core.middleware import log_request_middleware
from .api.v1.api import router as api_v1_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
app.middleware("http")(log_request_middleware)

# Include API router
app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

@app.get("/")
async def root():
    return {"message": "Welcome to FastAPI"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
