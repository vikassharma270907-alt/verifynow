"""Vercel serverless function entry point - wraps the FastAPI app."""

import sys
import os

# Add the backend directory to Python path so its internal imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Now import the FastAPI app - Vercel Python runtime picks up the `app` variable
from main import app  # noqa: E402
