"""Shared helpers for the audit tests. No live network: every httpx call is faked."""

import sys
from pathlib import Path

import httpx
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Captured before any test patches httpx.AsyncClient (used for ASGI in-process calls).
RealAsyncClient = httpx.AsyncClient


class FakeResponse:
    def __init__(self, payload=None, status_code: int = 200, text: str = ""):
        self._payload = payload
        self.status_code = status_code
        self.text = text or ""

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://fake.invalid")
            raise httpx.HTTPStatusError(
                "error", request=request, response=httpx.Response(self.status_code, request=request)
            )


def make_fake_client(handler, calls: list | None = None):
    """Build a stand-in for httpx.AsyncClient. handler(url, json, headers) -> FakeResponse | raises."""

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None, headers=None, **kwargs):
            if calls is not None:
                calls.append({"url": url, "json": json, "headers": headers or {}})
            result = handler(url, json, headers or {})
            if hasattr(result, "__await__"):
                result = await result
            return result

        async def get(self, url, headers=None, **kwargs):
            result = handler(url, None, headers or {})
            if hasattr(result, "__await__"):
                result = await result
            return result

    return FakeAsyncClient


def chat_response(content: str, total_tokens: int = 10) -> FakeResponse:
    return FakeResponse(
        {"choices": [{"message": {"content": content}}], "usage": {"total_tokens": total_tokens}}
    )


@pytest.fixture
def real_async_client():
    return RealAsyncClient
