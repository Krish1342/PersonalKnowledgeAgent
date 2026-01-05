"""
FastAPI application factory and configuration.
Entry point for the Personal Knowledge Agent backend.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.utils.logging import setup_logging, get_logger
from app.api import health

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Application starting up")
    yield
    # Shutdown
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """
    Application factory function.
    Creates and configures the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    # Setup logging
    setup_logging()

    # Create app instance
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router)

    # Root endpoint
    @app.get("/")
    def root() -> dict[str, str]:
        """Root endpoint."""
        return {
            "message": f"Welcome to {settings.APP_NAME}",
            "version": settings.APP_VERSION,
        }

    logger.info(
        f"Application initialized",
        extra={
            "app_name": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
        },
    )

    return app


# Application instance
app = create_app()
