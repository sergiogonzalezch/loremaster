"""Endpoints de monitoreo y health check."""

from fastapi import APIRouter

from app.services.health_service import check_services_health

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """Endpoint de health check para monitoreo."""
    return check_services_health()
