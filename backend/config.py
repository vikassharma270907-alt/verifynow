"""VerifyFlow configuration — model IDs, API endpoints, and tier routing rules."""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Nebius Token Factory
# ---------------------------------------------------------------------------
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY", "")
NEBIUS_BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1/")

# NVIDIA Nemotron models on Nebius Token Factory — tier routing
MODELS = {
    "nano": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",      # $0.06/1M in, $0.24/1M out — fast triage
    "nano_omni": "nvidia/Nemotron-3-Nano-Omni",           # $0.06/1M in — multimodal perception
    "super": "nvidia/Nemotron-3-Super-120b-a12b",          # $0.30/1M in, $0.90/1M out — deep analysis
    "super_vl": "nvidia/Nemotron-3.5-Super-VL",            # $0.30/1M in — visual document intelligence
    "ultra": "nvidia/Nemotron-3-Ultra-550b-a55b",          # $1.00/1M in, $3.00/1M out — final synthesis
}

# Default tier allocation for cost optimization
# Target: 85% Nano, 10% Super, 5% Ultra → ~120M tokens on $50 budget
TIER_ROUTING = {
    "claim_extraction": "nano",
    "entity_recognition": "nano",
    "classification": "nano",
    "deep_analysis": "super",
    "contradiction_detection": "super",
    "visual_document": "super_vl",
    "final_synthesis": "ultra",
    "complex_reasoning": "ultra",
}

# ---------------------------------------------------------------------------
# Tavily Search API
# ---------------------------------------------------------------------------
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_SEARCH_URL = "https://api.tavily.com/search"
TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
APP_NAME = "VerifyFlow"
APP_VERSION = "1.0.0"
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
MAX_UPLOAD_SIZE_MB = 20
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".png", ".jpg", ".jpeg", ".webp"}
