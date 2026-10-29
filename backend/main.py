"""VerifyFlow — AI-powered document verification with deterministic trust gates.

The model can think, but it does not get the final say. The evidence does.

Architecture:
  Nemotron-3-Nano (extract claims) → Tavily (live search) →
  Nemotron-3-Super (deep analysis) → Deterministic Code Verifier →
  Nemotron-3-Ultra (summary only) → Evidence Trust Scorecard
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import APP_NAME, APP_VERSION, LOG_LEVEL
from routers import baseline, health, verify, challenge
from services.model_router import validate_models

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Check configured model IDs against the provider at startup."""
    try:
        app.state.model_check = await validate_models()
    except Exception as exc:
        logger.error("Model validation failed: %s", exc)
        app.state.model_check = {}
    for tier, info in app.state.model_check.items():
        logger.info("Model tier %s: %s", tier, info)
    yield


app = FastAPI(
    lifespan=lifespan,
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "Document verification agent that extracts claims, cross-references them "
        "against live web evidence via Tavily, and produces an auditable trust "
        "scorecard. Powered by NVIDIA Nemotron on Nebius Token Factory."
    ),
)

_cors_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]
# On Vercel the frontend and API share the same origin, but if a custom
# domain is configured later it can be added via CORS_ORIGINS env var.
_extra = os.environ.get("CORS_ORIGINS", "")
if _extra:
    _cors_origins.extend([o.strip() for o in _extra.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(verify.router)
app.include_router(challenge.router)
app.include_router(baseline.router)


# ---------------------------------------------------------------------------
# Frontend (single-container deploy)
# ---------------------------------------------------------------------------
# If a built frontend exists (STATIC_DIR, default ./static), serve it at "/" so the
# UI and API share one origin. Otherwise "/" returns a small JSON description.
_static_dir = Path(os.environ.get("STATIC_DIR", Path(__file__).parent / "static"))

if (_static_dir / "index.html").is_file():
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="frontend")
else:

    @app.get("/")
    async def root():
        return {
            "app": APP_NAME,
            "version": APP_VERSION,
            "docs": "/docs",
            "pipeline": [
                "Deterministic checks on raw text (dates, look-alike domains, injected instructions)",
                "Nemotron Nano: claim extraction",
                "Tavily: web evidence per claim",
                "Nemotron Super: proposes stances and conflicts, with verbatim quotes",
                "Code verifier: decides every verdict (no model calls)",
                "Nemotron Ultra: summary",
            ],
        }
