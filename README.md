# VerifyFlow 📄✅

**AI-powered document verification with deterministic trust gates.**

> *The model can think, but it does not get the final say. The evidence does.*

VerifyFlow extracts every verifiable claim from a document, cross-references each one against live web evidence via Tavily, runs a **deterministic code-level verifier** (not an LLM) to make the final trust decision, and produces an auditable **Evidence Trust Scorecard**.

**Built for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/) — Best Apps & Agents track.**

---

## Architecture

```
Document Upload
       ↓
[Nemotron-3-Nano]  →  Extract claims ($0.06/1M tokens)
       ↓
[Tavily Search]    →  Live web evidence + citations
       ↓
[Nemotron-3-Super] →  Deep contradiction analysis ($0.30/1M) — high-stakes claims only
       ↓
[Code Verifier]    →  Deterministic trust gate (NO LLM)
       ↓
[Nemotron-3-Ultra] →  Human-readable summary ($1.00/1M) — called once
       ↓
Evidence Trust Scorecard
```

**Model tier routing**: 85% Nano / 10% Super / 5% Ultra → ~120M tokens on $50 budget.

## NVIDIA & Nebius Integration

| Component | How It's Used |
|-----------|---------------|
| **NVIDIA Nemotron-3-Nano-30B-A3B** | Fast claim extraction and classification |
| **NVIDIA Nemotron-3-Super-120b-a12b** | Deep contradiction detection for legal/financial claims |
| **NVIDIA Nemotron-3-Ultra-550b-a55b** | Final synthesis report generation |
| **Nebius Token Factory** | Unified OpenAI-compatible API serving all Nemotron models |
| **Tavily Search** | Real-time web grounding with citation URLs |

## Quick Start

### Prerequisites
- Docker and docker-compose
- Nebius Token Factory API key ([get one](https://studio.nebius.com/))
- Tavily API key ([get one](https://tavily.com/))

### Setup (< 5 minutes)

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/verifyflow.git
cd verifyflow

# 2. Configure environment
cp .env.example .env
# Edit .env and add your API keys

# 3. Run with Docker
docker-compose up --build

# 4. Open in browser
# Frontend: http://localhost:3000
# Backend API docs: http://localhost:8000/docs
```

### Run Without Docker

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Features

- **Drag-and-drop** document upload (PDF, text, images)
- **Evidence Trust Scorecard** — verified / unverifiable / contradicted counts
- **Expandable claim cards** with full evidence chains and source URLs
- **Challenge Mode** — pre-loaded adversarial inputs (homograph URLs, prompt injections, fabricated entities, contradictory terms)
- **Model tier usage** transparency — see exactly how many tokens each tier consumed
- **Deterministic verification** — the code verifier makes the final call, not the LLM

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python FastAPI |
| Frontend | React + Tailwind CSS + Vite |
| LLM Inference | Nebius Token Factory (OpenAI-compatible API) |
| Live Search | Tavily Search API |
| Containerization | Docker + docker-compose |

## License

[MIT](LICENSE)
