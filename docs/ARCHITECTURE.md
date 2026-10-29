# VerifyFlow Architecture

## Core Principle

> "The model can think, but it does not get the final say. The evidence does."

## Pipeline

```
Document → [Nemotron-3-Nano] Extract Claims ($0.06/1M)
               ↓
         [Tavily Search] Live Web Evidence
               ↓
         [Nemotron-3-Super] Deep Analysis ($0.30/1M) — only high-stakes claims
               ↓
         [Deterministic Code Verifier] — NOT an LLM — rule-based trust gate
               ↓
         [Nemotron-3-Ultra] Summary ($1.00/1M) — called once
               ↓
         Evidence Trust Scorecard
```

## Model Tier Routing

| Tier | Model | Cost | Usage |
|------|-------|------|-------|
| Nano | NVIDIA-Nemotron-3-Nano-30B-A3B | $0.06/1M in | 85% of calls — extraction, classification |
| Super | Nemotron-3-Super-120b-a12b | $0.30/1M in | 10% of calls — contradiction detection |
| Ultra | Nemotron-3-Ultra-550b-a55b | $1.00/1M in | 5% of calls — final summary only |

## Deterministic Verifier (No LLM)

The `evidence_verifier.py` makes all trust decisions using code, not models:
- Claim VERIFIED if: Tavily citation with relevance ≥ 0.7 supports it
- Claim CONTRADICTED if: Tavily citation with relevance ≥ 0.7 contradicts it
- Claim UNVERIFIABLE if: insufficient evidence in either direction

## Tech Stack

- **Backend**: Python FastAPI
- **Frontend**: React + Tailwind CSS + Vite
- **LLM Inference**: Nebius Token Factory (OpenAI-compatible)
- **Live Search**: Tavily Search API
- **Containerization**: Docker + docker-compose
- **Code Intelligence**: [Graphify](https://github.com/Graphify-Labs/graphify) knowledge graph

## Knowledge Graph (Graphify)

The project includes a Graphify knowledge graph (`graphify-out/`) that maps the entire codebase into a queryable graph of nodes and edges. This is used by Kiro for intelligent codebase navigation.

**Query the graph:**
```bash
graphify query "how does the verification pipeline work"
graphify path "evidence_verifier" "verify_document"
graphify explain "model_router"
```

**Rebuild after code changes:**
```bash
GRAPHIFY_BACKEND=none graphify extract . --code-only --update
graphify cluster-only .
```

**Setup for new contributors:**
```powershell
powershell -ExecutionPolicy Bypass -File "graphify-setup.ps1"
```

The graph is excluded from git (see `.gitignore`) and rebuilt locally. A Kiro hook auto-rebuilds it on file save.
