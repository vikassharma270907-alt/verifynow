"""Health check endpoint — confirms the API is running and dependencies are reachable."""

from fastapi import APIRouter
from config import NEBIUS_API_KEY, TAVILY_API_KEY, APP_VERSION

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": APP_VERSION,
        "nebius_configured": bool(NEBIUS_API_KEY),
        "tavily_configured": bool(TAVILY_API_KEY),
    }
