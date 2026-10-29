"""Model-tier router — dispatches tasks to the cheapest capable Nemotron model.

Uses raw httpx instead of the openai SDK to avoid the jiter DLL dependency
which is blocked by Windows Application Control policies.

Routing strategy (optimized for $50 hackathon budget):
  85% → Nano   ($0.06/1M in)  — classification, extraction, entity recognition
  10% → Super  ($0.30/1M in)  — deep analysis, contradiction detection
   5% → Ultra  ($1.00/1M in)  — final synthesis only
"""

import logging
import httpx

from config import NEBIUS_API_KEY, NEBIUS_BASE_URL, MODELS, TIER_ROUTING

logger = logging.getLogger(__name__)

# Track token usage per tier for reporting
_usage: dict[str, int] = {"nano": 0, "super": 0, "ultra": 0}


def get_usage() -> dict[str, int]:
    return dict(_usage)


def reset_usage() -> None:
    global _usage
    _usage = {"nano": 0, "super": 0, "ultra": 0}


async def call_model(
    task_type: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    response_format: dict | None = None,
) -> str:
    """Route a task to the appropriate Nemotron tier and return the completion.

    Uses raw httpx POST to the OpenAI-compatible Nebius endpoint,
    avoiding the openai SDK's jiter dependency.

    Args:
        task_type: Key from TIER_ROUTING (e.g. "claim_extraction", "deep_analysis")
        system_prompt: System message for the model
        user_prompt: User message content
        temperature: Sampling temperature (low for deterministic outputs)
        max_tokens: Maximum output tokens
        response_format: Optional JSON mode {"type": "json_object"}

    Returns:
        The model's text response.
    """
    if not NEBIUS_API_KEY:
        raise RuntimeError("NEBIUS_API_KEY is not set. Check your .env file.")

    tier = TIER_ROUTING.get(task_type, "nano")
    model_id = MODELS.get(tier, MODELS["nano"])

    logger.info("Routing task=%s -> tier=%s model=%s", task_type, tier, model_id)

    payload: dict = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format is not None:
        payload["response_format"] = response_format

    url = NEBIUS_BASE_URL.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {NEBIUS_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Nebius API error (%s) for task=%s: %s",
            exc.response.status_code,
            task_type,
            exc.response.text[:500],
        )
        raise
    except Exception:
        logger.exception("Nebius API call failed for task=%s tier=%s", task_type, tier)
        raise

    choice = data["choices"][0]
    text = choice["message"].get("content", "")

    # Track usage
    usage_data = data.get("usage")
    if usage_data:
        total = usage_data.get("total_tokens", 0)
        bucket = "nano" if tier in ("nano", "nano_omni") else ("ultra" if tier == "ultra" else "super")
        _usage[bucket] = _usage.get(bucket, 0) + total

    logger.info(
        "Completed task=%s tier=%s tokens=%s",
        task_type,
        tier,
        usage_data.get("total_tokens", "unknown") if usage_data else "unknown",
    )
    return text
