---
inclusion: always
---

# VerifyFlow — Project Context

## What This Is
VerifyFlow is an AI-powered document verification agent built for the **Nebius x NVIDIA Global AI Hackathon** (Best Apps & Agents track). Deadline: October 30, 2026.

## Core Principle
> "The model can think, but it does not get the final say. The evidence does."

Every LLM output is treated as an untrusted claim. A **deterministic code-level verifier** (`backend/services/evidence_verifier.py`) makes all final trust decisions — not the model.

## Architecture
- **Nemotron-3-Nano** ($0.06/1M) — claim extraction, classification (85% of calls)
- **Nemotron-3-Super** ($0.30/1M) — deep contradiction detection (10% of calls)
- **Nemotron-3-Ultra** ($1.00/1M) — summary generation only (5% of calls)
- **Tavily Search API** — live web grounding with citation URLs
- **Deterministic Code Verifier** — rule-based, no LLM, makes final verdict

## Stack
- Backend: Python FastAPI (`backend/`)
- Frontend: React + Tailwind + Vite (`frontend/`)
- Docker: `docker-compose.yml` for one-command setup
- API: Nebius Token Factory (OpenAI-compatible at `https://api.studio.nebius.com/v1/`)

## Key Files
- `backend/services/model_router.py` — tier routing logic
- `backend/services/evidence_verifier.py` — deterministic trust gate
- `backend/services/claim_extractor.py` — Nano-powered extraction
- `backend/services/tavily_grounder.py` — Tavily live search
- `backend/routers/verify.py` — main pipeline endpoint
- `backend/routers/challenge.py` — adversarial test cases
- `backend/config.py` — model IDs, API URLs, routing config

## Rules When Editing
1. Never pass raw LLM output directly to users — always verify first
2. Keep the evidence verifier deterministic (no LLM calls in `evidence_verifier.py`)
3. Route tasks to the cheapest capable model tier
4. All API keys come from environment variables, never hardcode
5. Maintain the 85/10/5 Nano/Super/Ultra cost split
