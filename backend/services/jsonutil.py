"""Tolerant JSON parsing for model output."""

import json
import re


def loads_loose(raw: str) -> dict:
    """Parse a JSON object from model output.

    Handles reasoning blocks (<think>...</think>), markdown code fences, and
    prose around the object. Raises json.JSONDecodeError if nothing parses.
    """
    text = re.sub(r"<think>.*?</think>", "", raw or "", flags=re.DOTALL).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise
