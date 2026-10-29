"""Preservation property tests (Property 2).

Observation-first: every expectation below was observed on the current (unfixed) code for inputs where
isBugCondition is false. These tests must PASS before the audit fixes and keep passing after them.

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11
No live network: every httpx call is faked.
"""

import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import date
from urllib.parse import urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings, strategies as st

from config import MODELS, TIER_ROUTING
from models.claim import Claim, ClaimStatus
from models.evidence import Evidence, EvidenceSource
from models.finding import DocumentFinding, FindingKind, Severity
from models.report import ClaimVerification, RiskLevel, VerificationReport
from services import document_checks, model_router, tavily_grounder
from services.evidence_verifier import (
    EVIDENCE_RELEVANCE_THRESHOLD,
    compute_risk_level,
    compute_trust_score,
    verify_claim,
)
from tests.conftest import BACKEND_DIR, REPO_DIR, FakeResponse, chat_response, make_fake_client

FAKE_KEY = "placeholder-key-for-tests"
FAST = settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])

CONTENT = "Acme Corp is registered in Ohio since 1999."
GOOD_QUOTE = "Acme Corp is registered"
BAD_QUOTE = "Totally invented quote text"


def make_claim(text="Acme Corp is registered in Ohio", entities=("Acme Corp",), cid="claim-1") -> Claim:
    return Claim(
        id=cid, text=text, category="legal", source_location="s1", confidence=0.9, entities=list(entities)
    )


def make_ev(i: int, stance: str, score: float, quote_ok: bool) -> Evidence:
    return Evidence(
        source_type=EvidenceSource.TAVILY_SEARCH,
        source_url=f"https://site{i}.example.org/p",
        source_title=f"Site {i}",
        content=CONTENT,
        supports_claim=stance == "supports",
        stance=stance,
        quote=(GOOD_QUOTE if quote_ok else BAD_QUOTE) if stance in ("supports", "contradicts") else None,
        relevance_score=score,
        retrieved_at="2026-01-01T00:00:00Z",
    )


# ---------------------------------------------------------------------------
# 3.5 Scoring formula and thresholds (non-empty claim lists)
# ---------------------------------------------------------------------------
def _statuses_to_claims(statuses):
    return [
        make_claim(cid=f"c{i}").model_copy(update={"status": ClaimStatus(s)}) for i, s in enumerate(statuses)
    ]


def _finding(kind, severity, with_claim):
    return DocumentFinding(
        kind=kind, severity=severity, quote="q", explanation="e", claim_id="c0" if with_claim else None
    )


_status_lists = st.lists(st.sampled_from(["verified", "unverifiable", "contradicted"]), min_size=1, max_size=12)
_findings = st.lists(
    st.builds(
        _finding,
        st.sampled_from(list(FindingKind)),
        st.sampled_from(list(Severity)),
        st.booleans(),
    ),
    max_size=6,
)


def _ref_counts(findings):
    high = medium = 0
    for f in findings:
        reflected = f.kind in (FindingKind.INVALID_DATE, FindingKind.INTERNAL_CONFLICT) and f.claim_id is not None
        if reflected:
            continue
        high += f.severity == Severity.HIGH
        medium += f.severity == Severity.MEDIUM
    return high, medium


def _ref_score(statuses, findings):
    n = len(statuses)
    v, u, c = (statuses.count(s) for s in ("verified", "unverifiable", "contradicted"))
    high, medium = _ref_counts(findings)
    base = 100.0 * (v + 0.35 * u) / n
    penalty = 30.0 * c + 25.0 * high + 10.0 * medium
    return round(max(0.0, min(100.0, base - penalty)), 1)


def _ref_risk(score, statuses, findings):
    c = statuses.count("contradicted")
    high, medium = _ref_counts(findings)
    if (high >= 1 and c >= 1) or c >= 3:
        return "critical"
    if high >= 1 or c >= 1 or medium >= 2:
        return "high"
    return "medium" if score < 75 else "low"


@FAST
@given(statuses=_status_lists, findings=_findings)
def test_scoring_matches_existing_formula_and_thresholds(statuses, findings):
    claims = _statuses_to_claims(statuses)
    score = compute_trust_score(claims, findings)
    assert 0.0 <= score <= 100.0
    assert score == _ref_score(statuses, findings)
    assert compute_risk_level(score, claims, findings) == _ref_risk(score, statuses, findings)


def test_scoring_worked_examples():
    # base 50, minus 30 for the contradiction
    assert compute_trust_score(_statuses_to_claims(["verified", "contradicted"]), []) == 20.0
    assert compute_trust_score(_statuses_to_claims(["verified", "verified"]), []) == 100.0
    assert compute_trust_score(_statuses_to_claims(["contradicted"]), []) == 0.0
    assert compute_risk_level(100.0, _statuses_to_claims(["verified"]), []) == "low"
    assert compute_risk_level(20.0, _statuses_to_claims(["verified", "contradicted"]), []) == "high"
    assert compute_risk_level(0.0, _statuses_to_claims(["contradicted"] * 3), []) == "critical"
    assert compute_risk_level(35.0, _statuses_to_claims(["unverifiable"]), []) == "medium"


# ---------------------------------------------------------------------------
# 3.2 / 3.3 / 3.4 Bucket logic: contradictions first, then support, else unverifiable
# ---------------------------------------------------------------------------
_ev_specs = st.lists(
    st.tuples(
        st.sampled_from(["supports", "contradicts", "irrelevant", "unjudged"]),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        st.booleans(),
    ),
    max_size=6,
)


def test_relevance_threshold_constant_is_unchanged():
    assert EVIDENCE_RELEVANCE_THRESHOLD == 0.5


@FAST
@given(specs=_ev_specs, override=st.sampled_from([None, "finding", "conflict"]))
def test_bucket_logic_contradictions_first_then_support_else_unverifiable(specs, override):
    claim = make_claim()
    evidence = [make_ev(i, *spec) for i, spec in enumerate(specs)]
    finding = (
        DocumentFinding(kind=FindingKind.INVALID_DATE, severity=Severity.HIGH, quote="q", explanation="bad date")
        if override == "finding"
        else None
    )
    conflict = "conflicts with another clause" if override == "conflict" else None

    def qualifies(stance):
        return [
            e
            for e, (s, score, ok) in zip(evidence, specs)
            if s == stance and score >= EVIDENCE_RELEVANCE_THRESHOLD and ok
        ]

    contradicting, supporting = qualifies("contradicts"), qualifies("supports")
    non_qualifying = [
        e
        for e, (s, score, ok) in zip(evidence, specs)
        if s in ("supports", "contradicts") and not (score >= EVIDENCE_RELEVANCE_THRESHOLD and ok)
    ]

    result = verify_claim(claim, evidence, "Acme Corp is a company.", finding=finding, conflict_reason=conflict)

    if override == "finding":
        assert result.status == ClaimStatus.CONTRADICTED and result.verification_reason == "bad date"
    elif override == "conflict":
        assert result.status == ClaimStatus.CONTRADICTED and result.verification_reason == conflict
    elif contradicting:
        assert result.status == ClaimStatus.CONTRADICTED
        assert result.verification_reason.startswith(f"Contradicted by {len(contradicting)} source(s)")
    elif supporting:
        assert result.status == ClaimStatus.VERIFIED
        assert result.verification_reason.startswith(f"Supported by {len(supporting)} independent source(s)")
        for ev in supporting[:3]:
            assert urlparse(ev.source_url).hostname in result.verification_reason
    else:
        assert result.status == ClaimStatus.UNVERIFIABLE
        assert result.verification_reason

    # Proposals that fail the quote / relevance gate are marked rejected, never kept as support.
    for ev in non_qualifying:
        assert ev.stance == "rejected" and ev.supports_claim is False


def test_unverifiable_without_any_evidence_or_document_mention():
    claim = verify_claim(make_claim(), [], "A document that never names the entity.")
    assert claim.status == ClaimStatus.UNVERIFIABLE
    assert claim.verification_reason == "No independent evidence found."


def test_agreeing_quoted_support_above_threshold_is_verified_with_cited_url():
    claim = verify_claim(make_claim(), [make_ev(1, "supports", 0.8, True)], "doc")
    assert claim.status == ClaimStatus.VERIFIED
    assert "site1.example.org" in claim.verification_reason


def test_contradiction_beats_support_when_both_qualify():
    evs = [make_ev(1, "supports", 0.9, True), make_ev(2, "contradicts", 0.9, True)]
    assert verify_claim(make_claim(), evs, "doc").status == ClaimStatus.CONTRADICTED


# ---------------------------------------------------------------------------
# 3.1 Verifier purity (AST check)
# ---------------------------------------------------------------------------
FORBIDDEN_ROOTS = {"httpx", "requests", "aiohttp", "urllib3", "socket", "openai", "anthropic", "http"}
FORBIDDEN_SERVICE_MODULES = {"model_router", "tavily_grounder", "deep_analyzer", "synthesizer", "claim_extractor"}


def test_evidence_verifier_imports_no_llm_or_network_modules():
    tree = ast.parse((BACKEND_DIR / "services" / "evidence_verifier.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported.add(module)
            imported.update(f"{module}.{a.name}" if module else a.name for a in node.names)
    assert imported, "expected to find imports"

    bad = set()
    for name in imported:
        parts = name.split(".")
        if parts[0] in FORBIDDEN_ROOTS or FORBIDDEN_SERVICE_MODULES & set(parts):
            bad.add(name)
        if parts[0] == "urllib" and len(parts) > 1 and parts[1] != "parse":
            bad.add(name)
    assert not bad, f"evidence_verifier must stay deterministic, found: {bad}"

    called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "call_model" not in called
    assert not any(isinstance(n, (ast.AsyncFunctionDef, ast.Await)) for n in ast.walk(tree))


# ---------------------------------------------------------------------------
# 3.6 Routing
# ---------------------------------------------------------------------------
def test_tier_routing_keys_and_assignments_unchanged():
    assert TIER_ROUTING == {
        "claim_extraction": "nano",
        "evidence_judgment": "super",
        "conflict_detection": "super",
        "final_synthesis": "ultra",
    }
    assert set(MODELS) == {"nano", "super", "ultra"}


# ---------------------------------------------------------------------------
# 3.7 Secrets
# ---------------------------------------------------------------------------
def test_env_file_is_git_ignored():
    lines = [ln.strip() for ln in (REPO_DIR / ".gitignore").read_text(encoding="utf-8").splitlines()]
    assert ".env" in lines


def test_no_hardcoded_credentials_in_backend_source():
    pattern = re.compile(r"(?:sk-|tvly-|nebius-)[A-Za-z0-9_\-]{16,}")
    offenders = []
    for path in list(BACKEND_DIR.rglob("*.py")) + [REPO_DIR / "api" / "index.py"]:
        if "tests" in path.parts or "__pycache__" in path.parts:
            continue
        if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
            offenders.append(str(path))
    assert not offenders


def _run_backend_snippet(code: str, env_extra: dict[str, str]) -> str:
    env = {k: v for k, v in os.environ.items() if k not in ("NEBIUS_API_KEY", "TAVILY_API_KEY", "CORS_ORIGINS")}
    env.update(env_extra)
    out = subprocess.run(
        [sys.executable, "-c", code], cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=90
    )
    assert out.returncode == 0, out.stderr[-500:]
    return out.stdout.strip().splitlines()[-1]


def test_api_keys_are_read_from_environment():
    code = "import config; print(config.NEBIUS_API_KEY + '|' + config.TAVILY_API_KEY)"
    assert _run_backend_snippet(code, {"NEBIUS_API_KEY": "env-n", "TAVILY_API_KEY": "env-t"}) == "env-n|env-t"


# ---------------------------------------------------------------------------
# 3.8 Schemas
# ---------------------------------------------------------------------------
def test_model_field_names_unchanged():
    assert list(Claim.model_fields) == [
        "id", "text", "category", "source_location", "confidence", "status", "verification_reason", "entities",
    ]
    assert list(Evidence.model_fields) == [
        "source_type", "source_url", "source_title", "content", "supports_claim", "stance", "quote",
        "relevance_score", "retrieved_at",
    ]
    assert list(ClaimVerification.model_fields) == ["claim", "evidence", "verdict"]
    assert list(VerificationReport.model_fields) == [
        "document_name", "document_type", "total_claims", "verified_count", "unverifiable_count",
        "contradicted_count", "risk_level", "trust_score", "claim_verifications", "findings",
        "analysis_notes", "summary", "model_tier_usage", "processing_time_ms",
    ]
    assert [r.value for r in RiskLevel] == ["low", "medium", "high", "critical"]


# ---------------------------------------------------------------------------
# Pipeline with mocked upstreams: valid uploads return a schema-valid report (3.6, 3.8)
# ---------------------------------------------------------------------------
def make_pdf(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


DOC_TEXT = "Acme Corp is registered in Ohio. Acme Corp employs staff in Ohio."


@pytest.fixture
def upstream(monkeypatch):
    """Fake Nebius + Tavily. Returns the list of recorded calls."""
    calls: list[dict] = []

    def handler(url, body, headers):
        if "tavily" in url:
            return FakeResponse(
                {"results": [{"url": "https://registry.example.org/acme", "title": "Registry", "content": CONTENT, "score": 0.9}]}
            )
        model, system, user = body["model"], body["messages"][0]["content"], body["messages"][1]["content"]
        if model == MODELS["nano"]:
            claims = [
                {"text": "Acme Corp is registered in Ohio", "category": "legal", "source_location": "p1",
                 "confidence": 0.9, "entities": ["Acme Corp"]},
                {"text": "Acme Corp employs staff in Ohio", "category": "factual", "source_location": "p1",
                 "confidence": 0.8, "entities": ["Acme Corp"]},
            ]
            return chat_response(json.dumps({"claims": claims}), 10)
        if model == MODELS["super"]:
            if "web search snippets" in system:
                ids = re.findall(r"CLAIM (claim-[0-9a-f]+):", user)
                judgments = [{"claim_id": i, "source": 1, "stance": "supports", "quote": GOOD_QUOTE} for i in ids]
                return chat_response(json.dumps({"judgments": judgments}), 20)
            return chat_response(json.dumps({"conflicts": []}), 20)
        return chat_response("The document describes a company registration.", 30)

    monkeypatch.setattr(httpx, "AsyncClient", make_fake_client(handler, calls))
    monkeypatch.setattr(model_router, "NEBIUS_API_KEY", FAKE_KEY)
    monkeypatch.setattr(tavily_grounder, "TAVILY_API_KEY", FAKE_KEY)
    return calls


@pytest.fixture
def client():
    from main import app

    return TestClient(app, raise_server_exceptions=False)


def _uploads():
    return {
        "utf8": ("doc.txt", (DOC_TEXT + " Café.").encode("utf-8")),
        "latin1": ("doc.txt", (DOC_TEXT + " Café.").encode("latin-1")),
        "markdown": ("doc.md", DOC_TEXT.encode("utf-8")),
        "pdf": ("doc.pdf", make_pdf(DOC_TEXT)),
    }


@pytest.mark.parametrize("kind", ["utf8", "latin1", "markdown", "pdf"])
def test_valid_uploads_return_schema_valid_report_with_expected_routing(upstream, client, kind):
    name, data = _uploads()[kind]
    resp = client.post("/api/verify", files={"file": (name, data)})
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert set(body) == set(VerificationReport.model_fields)
    report = VerificationReport.model_validate(body)
    assert report.document_name == name
    assert report.total_claims == 2 == len(report.claim_verifications)
    assert report.verified_count == 2 and report.contradicted_count == 0
    assert all(cv.verdict == "verified" for cv in report.claim_verifications)
    assert "registry.example.org" in report.claim_verifications[0].claim.verification_reason
    assert "The document describes a company registration." in report.summary
    assert 0 <= report.trust_score <= 100
    assert all(report.model_tier_usage[t] > 0 for t in ("nano", "super", "ultra"))

    models_called = [c["json"]["model"] for c in upstream if c.get("json") and "model" in c["json"]]
    assert models_called.count(MODELS["nano"]) == 1  # Nano extracts once
    assert models_called.count(MODELS["ultra"]) == 1  # Ultra summarizes once
    assert models_called.count(MODELS["super"]) >= 1  # Super judges / detects conflicts


# ---------------------------------------------------------------------------
# 3.9 Routes
# ---------------------------------------------------------------------------
def test_health_shape(client):
    body = client.get("/health").json()
    assert set(body) == {"status", "version", "nebius_configured", "tavily_configured", "models", "models_ok"}
    assert body["status"] == "ok"
    assert isinstance(body["nebius_configured"], bool) and isinstance(body["tavily_configured"], bool)


def test_root_shape(client):
    body = client.get("/").json()
    assert set(body) == {"app", "version", "docs", "architecture"}
    assert body["app"] == "VerifyFlow" and body["docs"] == "/docs"
    assert set(body["architecture"]) == {"stage_1", "stage_2", "stage_3", "stage_4", "stage_5"}


KNOWN_CHALLENGES = {"homograph-attack", "prompt-injection", "fabricated-entity", "contradictory-terms"}


def test_challenge_list_shape(client):
    body = client.get("/api/challenges").json()
    assert isinstance(body, list)
    assert {c["id"] for c in body} == KNOWN_CHALLENGES
    assert all(set(c) == {"id", "name", "description"} for c in body)


@pytest.mark.parametrize("cid", sorted(KNOWN_CHALLENGES))
def test_known_challenge_returns_full_text(client, cid):
    body = client.get(f"/api/challenges/{cid}").json()
    assert body["id"] == cid
    assert len(body["document_text"]) > 50
    assert body["expected_flags"]
    assert {"name", "description"} <= set(body)


# ---------------------------------------------------------------------------
# 3.10 Deployment entry point and rewrites
# ---------------------------------------------------------------------------
def test_vercel_entry_point_exposes_main_app():
    import main

    spec = importlib.util.spec_from_file_location("vercel_entry_under_test", REPO_DIR / "api" / "index.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.app is main.app


def test_vercel_rewrites_for_api_and_health_exist():
    config = json.loads((REPO_DIR / "vercel.json").read_text(encoding="utf-8"))
    rewrites = {r["source"]: r["destination"] for r in config["rewrites"]}
    assert rewrites["/api/(.*)"] == "/api/index"
    assert rewrites["/health"] == "/api/index"


# ---------------------------------------------------------------------------
# 3.11 CORS
# ---------------------------------------------------------------------------
def _preflight(client, origin):
    return client.options(
        "/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
    ).headers.get("access-control-allow-origin")


@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://localhost:5173"])
def test_default_cors_origins_allowed(client, origin):
    assert _preflight(client, origin) == origin


def test_unlisted_origin_is_not_allowed(client):
    assert _preflight(client, "https://evil.example.com") is None


def test_cors_origins_env_var_extends_defaults():
    code = (
        "import main\n"
        "mw = [m for m in main.app.user_middleware if m.cls.__name__ == 'CORSMiddleware'][0]\n"
        "opts = getattr(mw, 'kwargs', None) or getattr(mw, 'options')\n"
        "print(','.join(opts['allow_origins']))"
    )
    out = _run_backend_snippet(code, {"CORS_ORIGINS": "https://a.example.com, https://b.example.com"})
    assert out.split(",") == [
        "http://localhost:3000", "http://localhost:5173", "https://a.example.com", "https://b.example.com",
    ]


# ---------------------------------------------------------------------------
# Dates already accepted today stay accepted
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text",
    ["Signed 2026-03-15.", "Signed 15/03/2026.", "Signed 03/15/2026.", "Signed March 15, 2026.",
     "Signed 15 March 2026.", "Signed 29 February 2024."],
)
def test_valid_dates_are_not_flagged(text):
    assert document_checks.check_dates(text) == []


@FAST
@given(d=st.dates(min_value=date(1990, 1, 1), max_value=date(2099, 12, 31)))
def test_property_real_calendar_dates_are_never_flagged(d):
    forms = [
        f"{d.year}-{d.month:02d}-{d.day:02d}",
        f"{d.day:02d}/{d.month:02d}/{d.year}",
        f"{d.day:02d}-{d.month:02d}-{d.year}",
        f"{d.strftime('%B')} {d.day}, {d.year}",
    ]
    for form in forms:
        assert document_checks.check_dates(f"Effective {form}.") == [], form
