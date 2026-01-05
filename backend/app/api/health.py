"""
Health check endpoints for monitoring application status.
"""

from datetime import datetime
from fastapi import APIRouter, status
from pydantic import BaseModel

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: datetime
    version: str
    environment: str


@router.get("/", response_model=HealthCheckResponse, status_code=status.HTTP_200_OK)
def health_check() -> HealthCheckResponse:
    """
    Health check endpoint.

    Returns:
        Health status with timestamp and version info
    """
    settings = get_settings()
    logger.info("Health check requested")

    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.get("/live", status_code=status.HTTP_200_OK)
def liveness_check() -> dict[str, str]:
    """
    Liveness probe for Kubernetes/container orchestration.
    Indicates if the application is running.
    """
    return {"status": "alive"}


@router.get("/ready", status_code=status.HTTP_200_OK)
def readiness_check() -> dict[str, str]:
    """
    Readiness probe for Kubernetes/container orchestration.
    Indicates if the application is ready to accept requests.
    """
    return {"status": "ready"}
