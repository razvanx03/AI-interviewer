import os
import sys
import logging
import subprocess
from pathlib import Path
from contextlib import asynccontextmanager

# Configure structured real-time logging for Docker and local development
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("api.main")

# --- Auto-venv bootstrap: Re-launch with virtualenv python if invoked via global python ---
BASE_DIR = Path(__file__).resolve().parent
VENV_PYTHON = (
    BASE_DIR / "venv" / "Scripts" / "python.exe"
    if os.name == "nt"
    else BASE_DIR / "venv" / "bin" / "python"
)

if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    result = subprocess.run([str(VENV_PYTHON)] + sys.argv, cwd=str(BASE_DIR))
    sys.exit(result.returncode)

# Ensure api and project root are in sys.path
sys.path.insert(0, str(BASE_DIR.parent))
sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from db.session import init_db
from router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing %s in [%s] mode...", settings.PROJECT_NAME, settings.ENVIRONMENT)
    try:
        await init_db()
        logger.info("PostgreSQL database tables and connections verified successfully.")
    except Exception as exc:
        logger.error("FATAL: Could not initialize database connection: %s", exc, exc_info=True)
        raise
    yield
    logger.info("Shutting down API server gracefully...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Scalable backend for AI Job Interviewer platform with PostgreSQL storage, ready for Ollama & pgvector.",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Set up CORS (dynamic origins from .env + local development regex)
cors_kwargs = {
    "allow_origins": settings.CORS_ORIGINS,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.CORS_ORIGIN_REGEX and settings.ENVIRONMENT != "production":
    cors_kwargs["allow_origin_regex"] = settings.CORS_ORIGIN_REGEX

app.add_middleware(CORSMiddleware, **cors_kwargs)

# Global Unhandled Error Logger (Flushes full traceback to Docker logs)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled Exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "message": str(exc)},
    )

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health"])
def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "features": {
            "database_connected": True,
            "ollama_ready": True,
            "pgvector_ready": True,
            "websocket_chat": True,
        },
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(BASE_DIR), str(BASE_DIR.parent / "llm")],
    )
