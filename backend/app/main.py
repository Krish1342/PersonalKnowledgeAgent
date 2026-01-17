from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ingest_router, query_router, memory_router
from app.api.memory_v2 import router as memory_v2_router
from app.config import settings
from app.auth.clerk import get_clerk_auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Handles startup and shutdown events.
    """
    # Startup: ensure data directories exist
    Path(settings.VECTOR_DB_PATH).mkdir(parents=True, exist_ok=True)
    Path(settings.SQLITE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    yield

    # Shutdown: cleanup if needed
    pass


# Initialize FastAPI application
app = FastAPI(
    title="Personal Knowledge Base Agent",
    description="A RAG-powered personal knowledge base with LangGraph agent workflow",
    version="2.0.0",
    lifespan=lifespan,
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(ingest_router, prefix="/api")
app.include_router(query_router, prefix="/api")
app.include_router(memory_router, prefix="/api")  # Legacy memory API
app.include_router(memory_v2_router, prefix="/api/v2")  # Enhanced memory API


@app.get("/", tags=["health"])
async def root():
    """Root endpoint - health check."""
    clerk = get_clerk_auth()
    return {
        "status": "healthy",
        "service": "Personal Knowledge Base Agent",
        "version": "2.0.0",
        "auth_enabled": clerk.is_enabled,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Detailed health check endpoint."""
    clerk = get_clerk_auth()
    return {
        "status": "healthy",
        "vector_db_path": settings.VECTOR_DB_PATH,
        "sqlite_db_path": settings.SQLITE_DB_PATH,
        "embedding_model": settings.MODEL_NAME,
        "llm_configured": bool(settings.GROQ_API_KEY),
        "auth_enabled": clerk.is_enabled,
        "environment": settings.ENVIRONMENT,
    }
