"""Health check endpoint."""

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
    }


@router.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "name": "POC Factory",
        "version": "0.1.0",
        "description": "Agentic POC generation platform",
        "docs": "/docs",
        "health": "/health",
    }
