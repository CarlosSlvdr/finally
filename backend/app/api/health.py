"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
async def health() -> dict:
    """Simple liveness check for Docker/deployment."""
    return {"status": "ok"}
