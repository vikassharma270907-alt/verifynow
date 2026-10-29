"""VerifyFlow — AI-powered document verification with deterministic trust gates.

The model can think, but it does not get the final say. The evidence does.

Architecture:
  Nemotron-3-Nano (extract claims) → Tavily (live search) →
  Nemotron-3-Super (deep analysis) → Deterministic Code Verifier →
  Nemotron-3-Ultra (summary only) → Evidence Trust Scorecard
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import APP_NAME, APP_VERSION, LOG_LEVEL
from routers import health, verify, challenge

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
app = FastAPI(
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
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(verify.router)
app.include_router(challenge.router)


@app.get("/")
async def root():
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "docs": "/docs",
        "architecture": {
            "stage_1": "Nemotron-3-Nano → Claim extraction ($0.06/1M)",
            "stage_2": "Tavily Search → Live web grounding",
            "stage_3": "Nemotron-3-Super → Deep contradiction analysis ($0.30/1M)",
            "stage_4": "Deterministic Code Verifier → Trust gate (NO LLM)",
            "stage_5": "Nemotron-3-Ultra → Summary generation ($1.00/1M)",
        },
    }
