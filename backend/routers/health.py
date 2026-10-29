"""Health check: confirms keys are configured and each model tier's ID exists on the provider."""

from fastapi import APIRouter, Request

from config import APP_VERSION, NEBIUS_API_KEY, TAVILY_API_KEY

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(request: Request):
    models = getattr(request.app.state, "model_check", None)
    models_ok = None if not models else all(info["available"] for info in models.values())
    return {
        "status": "ok",
        "version": APP_VERSION,
        "nebius_configured": bool(NEBIUS_API_KEY),
        "tavily_configured": bool(TAVILY_API_KEY),
        "models": models,
        "models_ok": models_ok,
    }
