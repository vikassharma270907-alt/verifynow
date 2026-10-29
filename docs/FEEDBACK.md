# Platform Feedback — VerifyFlow

## Models Used

- `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` — claim extraction, classification, entity recognition
- `nvidia/Nemotron-3-Super-120b-a12b` — deep clause analysis, contradiction detection
- `nvidia/Nemotron-3-Ultra-550b-a55b` — final synthesis report generation
- Tavily Search API — live web grounding and citation verification

## Zero-to-Hello-World Experience

- **Time from signup to first API call**: ~8 minutes
- **Friction**: OpenAI-compatible API made integration straightforward with the `openai` Python SDK
- **Positive**: Model IDs are well-documented; switching between tiers uses the same base URL
- **Region tested**: us-central1

## Nebius Token Factory

### What Worked Well
- The unified OpenAI-compatible endpoint (`https://api.studio.nebius.com/v1/`) made it trivial to swap models by changing a single model ID string
- JSON mode (`response_format: {"type": "json_object"}`) worked reliably across all Nemotron tiers
- Token usage is accurately reported in the response, enabling real-time budget tracking

### Areas for Improvement
- Document the exact model ID casing requirements more prominently (case-sensitive)
- Provide example latency benchmarks for different regions in the docs

## Tavily Search API

### What Worked Well
- `search_depth: "advanced"` returns high-quality results relevant to verification tasks
- Response schema is clean and well-structured for programmatic consumption

## Would I Adopt in Production?

Yes — the tier routing economics are compelling. Running 85% of traffic on Nano ($0.06/1M) while reserving Ultra for synthesis-only keeps costs manageable at scale. The OpenAI-compatible API removes migration friction for teams already on OpenAI.
