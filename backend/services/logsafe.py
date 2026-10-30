"""Helpers that keep secrets and document content out of logs and responses."""

import os
import re
from urllib.parse import urlsplit

_SECRET_ENV_NAMES = ("NEBIUS_API_KEY", "TAVILY_API_KEY")
_BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+")
_KEYLIKE = re.compile(r"\b(?:tvly|sk|eyJ)[A-Za-z0-9_-]{16,}")


def safe_excerpt(value: object, limit: int = 200) -> str:
    """Single-line, length-capped text with configured secrets and bearer tokens removed."""
    text = str(value)
    for name in _SECRET_ENV_NAMES:
        secret = os.environ.get(name, "")
        if len(secret) >= 8:
            text = text.replace(secret, "[redacted]")
    text = _BEARER.sub("Bearer [redacted]", text)
    text = _KEYLIKE.sub("[redacted]", text)
    text = " ".join("".join(ch if ch.isprintable() else " " for ch in text).split())
    return text[:limit]


def safe_http_url(value: object, limit: int = 2048) -> str | None:
    """Return the URL only if it is a plain http(s) URL with a host; otherwise None."""
    if not isinstance(value, str):
        return None
    url = value.strip()
    if not url or len(url) > limit or any(ord(ch) < 32 or ch.isspace() for ch in url):
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        return None
    return url
