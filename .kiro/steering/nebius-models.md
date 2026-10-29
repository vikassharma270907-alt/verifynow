---
inclusion: auto
name: nebius-models
description: Nebius Token Factory model IDs, pricing, and routing guidance for NVIDIA Nemotron models
---

# Nebius Token Factory — Model Reference

## API Endpoint
```
Base URL: https://api.studio.nebius.com/v1/
Auth: Bearer token via NEBIUS_API_KEY
Compatible: OpenAI Python SDK
```

## Available Nemotron Models

| Model ID | Tier | Input $/1M | Output $/1M | Speed | Use For |
|----------|------|-----------|------------|-------|---------|
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | Nano | $0.06 | $0.24 | 60 Tok/s | Fast triage, RAG, extraction |
| `nvidia/Nemotron-3-Nano-Omni` | Nano | $0.06 | $0.24 | 90 Tok/s | Multimodal, tool routing |
| `nvidia/Nemotron-3-Super-120b-a12b` | Super | $0.30 | $0.90 | 127 Tok/s | Multi-agent, code analysis |
| `nvidia/Nemotron-3.5-Super-VL` | Super | $0.30 | $0.90 | N/A | Visual document intelligence |
| `nvidia/Nemotron-3-Ultra-550b-a55b` | Ultra | $1.00 | $3.00 | 59 Tok/s | Deep research, planning |

## Routing Rules for $50 Budget
- 85% traffic → Nano ($0.06/1M) — extraction, classification, entity recognition
- 10% traffic → Super ($0.30/1M) — contradiction detection, deep analysis
- 5% traffic → Ultra ($1.00/1M) — final synthesis only
- A pure Ultra pipeline ≈ 16.6M output tokens
- Tiered pipeline ≈ 120M+ tokens
