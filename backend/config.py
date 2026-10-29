"""VerifyFlow configuration: model IDs, API endpoints, and tier routing rules."""

import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Nebius Token Factory (OpenAI-compatible API)
# ---------------------------------------------------------------------------
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY", "")
NEBIUS_BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1/")

# Model IDs are case-sensitive. These were checked against GET /v1/models;
# the server also re-checks them at startup (see main.py) and reports on /health.
MODELS = {
    "nano": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",   # fast, cheap: claim extraction
    "super": "nvidia/nemotron-3-super-120b-a12b",      # mid tier: evidence judgment, conflict detection
    "ultra": "nvidia/Nemotron-3-Ultra-550b-a55b",      # largest: final summary only
}

# Which tier handles which task. Models only PROPOSE; evidence_verifier.py decides.
TIER_ROUTING = {
    "claim_extraction": "nano",
    "evidence_judgment": "super",
    "conflict_detection": "super",
    "final_synthesis": "ultra",
    "baseline_review": "ultra",  # the "plain LLM" comparison; informational only, never feeds a verdict
}

# ---------------------------------------------------------------------------
# Tavily Search API
# ---------------------------------------------------------------------------
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_SEARCH_URL = "https://api.tavily.com/search"

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
APP_NAME = "VerifyFlow"
APP_VERSION = "1.1.0"
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
# Vercel serverless functions reject request bodies above ~4.5 MB, so default to 4.
# Raise via MAX_UPLOAD_SIZE_MB when self-hosting (Docker).
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "4"))
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
