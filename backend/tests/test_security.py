"""Security regression tests: log redaction, URL schemes, client identity, PDF cap."""

import io

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from routers import verify
from services.logsafe import safe_excerpt, safe_http_url


def _request(headers: dict[str, str], client_host: str = "10.0.0.9") -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (client_host, 1234),
    }
    return Request(scope)


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "data:text/html,x", "file:///etc/passwd", "ftp://x.test/a", "//x.test", "", None, 5,
     "https://", "https://a.test/ b"],
)
def test_non_http_urls_are_dropped(url):
    assert safe_http_url(url) is None


def test_http_and_https_urls_pass():
    assert safe_http_url("https://example.com/a?b=1") == "https://example.com/a?b=1"
    assert safe_http_url("http://example.com") == "http://example.com"


def test_safe_excerpt_redacts_configured_keys_and_bearer(monkeypatch):
    fake = "placeholder-not-a-real-value"
    monkeypatch.setenv("NEBIUS_API_KEY", fake)
    out = safe_excerpt(f"bad key {fake} and Authorization: Bearer abc.def-ghi\nnext", 300)
    assert fake not in out
    assert "abc.def-ghi" not in out
    assert "\n" not in out


def test_forwarded_for_is_ignored_when_proxy_not_trusted(monkeypatch):
    monkeypatch.setattr(verify, "TRUST_PROXY_HEADERS", False)
    req = _request({"x-forwarded-for": "1.1.1.1, 2.2.2.2", "x-real-ip": "3.3.3.3"})
    assert verify._client_id(req) == "10.0.0.9"


def test_trusted_proxy_uses_platform_header_then_rightmost_xff(monkeypatch):
    monkeypatch.setattr(verify, "TRUST_PROXY_HEADERS", True)
    assert verify._client_id(_request({"x-vercel-forwarded-for": "9.9.9.9", "x-forwarded-for": "1.1.1.1"})) == "9.9.9.9"
    assert verify._client_id(_request({"x-forwarded-for": "6.6.6.6, 7.7.7.7"})) == "7.7.7.7"


def test_pdf_page_cap_rejects_huge_documents(monkeypatch):
    from PyPDF2 import PdfWriter

    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    monkeypatch.setattr(verify, "MAX_PDF_PAGES", 2)
    with pytest.raises(HTTPException) as err:
        verify._extract_text("a.pdf", buf.getvalue())
    assert err.value.status_code == 413
