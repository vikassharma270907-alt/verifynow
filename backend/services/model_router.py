"""Model-tier router: sends each task to the configured Nemotron tier.

Uses raw httpx against Nebius Token Factory's OpenAI-compatible endpoint instead
of the openai SDK. On the development machine the SDK's jiter dependency was
blocked by a Windows Application Control policy.
"""

import logging
from contextvars import ContextVar
from dataclasses import dataclass, field

import httpx

from config import MODELS, NEBIUS_API_KEY, NEBIUS_BASE_URL, TIER_ROUTING

from .errors import UpstreamError
from .logsafe import safe_excerpt

logger = logging.getLogger(__name__)

# Maps every routable tier (including vision variants) to a reporting bucket.
TIER_BUCKETS: dict[str, str] = {
    "nano": "nano",
    "nano_omni": "nano",
    "super": "super",
    "super_vl": "super",
    "ultra": "ultra",
}
_BUCKETS = ("nano", "super", "ultra")


@dataclass
class UsageTracker:
    """Per-request token and escalation counters."""

    tokens: dict[str, int] = field(default_factory=lambda: {b: 0 for b in _BUCKETS})
    super_calls: int = 0


# One tracker per request. Tasks spawned inside a request inherit the same
# tracker object; concurrent requests each set their own.
_tracker: ContextVar[UsageTracker | None] = ContextVar("usage_tracker", default=None)


def start_request_usage() -> UsageTracker:
    """Install a fresh tracker for the current request context."""
    tracker = UsageTracker()
    _tracker.set(tracker)
    return tracker


def reset_usage() -> None:
    """Backward-compatible alias for start_request_usage()."""
    start_request_usage()


def get_usage() -> dict[str, int]:
    tracker = _tracker.get()
    if tracker is None:
        return {b: 0 for b in _BUCKETS}
    return {b: tracker.tokens.get(b, 0) for b in _BUCKETS}


def get_super_calls() -> int:
    """Number of Super-tier calls made in the current request."""
    tracker = _tracker.get()
    return tracker.super_calls if tracker else 0


def _url(path: str) -> str:
    return NEBIUS_BASE_URL.rstrip("/") + path


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {NEBIUS_API_KEY}", "Content-Type": "application/json"}


async def validate_models() -> dict[str, dict]:
    """Check each configured model ID against the provider's model list.

    available is True/False, or None when the list could not be fetched.
    """
    result: dict[str, dict] = {tier: {"model": mid, "available": None} for tier, mid in MODELS.items()}
    if not NEBIUS_API_KEY:
        return result
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(_url("/models"), headers=_headers())
            resp.raise_for_status()
            listed = {m.get("id") for m in resp.json().get("data", [])}
    except Exception as exc:
        logger.warning("Could not fetch the model list for validation: %s", type(exc).__name__)
        return result
    for tier, info in result.items():
        info["available"] = info["model"] in listed
    return result


async def call_model(
    task_type: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    response_format: dict | None = None,
) -> str:
    """Route a task to its tier and return the completion text.

    Raises UpstreamError (with a user-safe message) on any upstream failure.
    """
    if not NEBIUS_API_KEY:
        raise UpstreamError(503, "Model service is not configured")

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

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(_url("/chat/completions"), json=payload, headers=_headers())
            if resp.status_code == 400 and response_format is not None:
                logger.warning("Model %s rejected response_format; retrying without it", model_id)
                payload.pop("response_format")
                resp = await client.post(_url("/chat/completions"), json=payload, headers=_headers())
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        # Log status and a redacted, truncated body only; never headers or the key.
        logger.error(
            "Nebius API error %s for task=%s model=%s: %s",
            code, task_type, model_id, safe_excerpt(exc.response.text, 300),
        )
        raise UpstreamError(503 if code == 429 else 502, f"Model service returned an error ({code})") from None
    except httpx.TimeoutException:
        logger.error("Nebius API timed out for task=%s model=%s", task_type, model_id)
        raise UpstreamError(502, "Model service timed out") from None
    except httpx.HTTPError as exc:
        logger.error("Nebius API call failed for task=%s model=%s: %s", task_type, model_id, type(exc).__name__)
        raise UpstreamError(502, "Model service is unreachable") from None
    except ValueError:
        logger.error("Nebius API returned non-JSON for task=%s model=%s", task_type, model_id)
        raise UpstreamError(502, "Model service returned an invalid response") from None

    try:
        text = data["choices"][0]["message"].get("content") or ""
        usage = data.get("usage") or {}
        tokens = int(usage.get("total_tokens", 0))
    except (KeyError, IndexError, TypeError, AttributeError, ValueError):
        logger.error("Nebius API returned an unexpected shape for task=%s model=%s", task_type, model_id)
        raise UpstreamError(502, "Model service returned an invalid response") from None

    bucket = TIER_BUCKETS.get(tier)
    if bucket is None:
        logger.warning("Unknown model tier %r for task=%s; tokens not attributed", tier, task_type)
    else:
        tracker = _tracker.get()
        if tracker is None:
            tracker = start_request_usage()
        tracker.tokens[bucket] = tracker.tokens.get(bucket, 0) + tokens
        if bucket == "super":
            tracker.super_calls += 1
    logger.info("Completed task=%s tier=%s tokens=%s", task_type, tier, tokens)
    return text