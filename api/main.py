import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure api and project root are in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parent))
sys.path.insert(0, str(BASE_DIR))

from core.config import settings
from router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Scalable backend for AI Job Interviewer platform with mock endpoints ready for Ollama & pgvector.",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health"])
def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy", 
        "project": settings.PROJECT_NAME,
        "features": {
            "ollama_ready": True,
            "pgvector_ready": True,
            "websocket_chat": True
        }
    }
