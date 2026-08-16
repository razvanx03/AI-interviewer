import os
import sys
import subprocess
from pathlib import Path

# --- Auto-venv bootstrap: Re-launch with virtualenv python if invoked via global python ---
BASE_DIR = Path(__file__).resolve().parent
VENV_PYTHON = BASE_DIR / "venv" / "Scripts" / "python.exe" if os.name == "nt" else BASE_DIR / "venv" / "bin" / "python"

if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    result = subprocess.run([str(VENV_PYTHON)] + sys.argv, cwd=str(BASE_DIR))
    sys.exit(result.returncode)

# Ensure api and project root are in sys.path
sys.path.insert(0, str(BASE_DIR.parent))
sys.path.insert(0, str(BASE_DIR))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from db.session import init_db
from router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    await init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Scalable backend for AI Job Interviewer platform with PostgreSQL storage, ready for Ollama & pgvector.",
    version="1.0.0",    
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
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
            "database_connected": True,
            "ollama_ready": True,
            "pgvector_ready": True,
            "websocket_chat": True,
        },
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

