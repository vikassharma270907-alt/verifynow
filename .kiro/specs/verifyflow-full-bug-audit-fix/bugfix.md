# Bugfix Requirements Document

## Introduction

This document captures the results of a full audit of VerifyFlow (FastAPI backend in `backend/`, Vercel entry `api/index.py`, React frontend in `frontend/`, Docker and deployment config). The audit was guided by the project rules (deterministic `evidence_verifier.py`, no raw LLM output shown to users, API keys only from environment, 85/10/5 Nano/Super/Ultra routing) and by the review checklists of the code-reviewer, security-reviewer and python-reviewer agents.

The most serious defects undermine the core promise ("the evidence gets the final say"): claims are marked VERIFIED without real corroboration, an LLM verdict flows straight into the deterministic gate, and the LLM-written summary reaches users unchecked. Further defects cause valid dates to be flagged as contradictions, crashes on malformed model output, cross-request state corruption, upload and timeout hazards, and broken Docker and frontend behavior.

The bug condition is a union of the defect classes below, referenced as C1 to C14.

## Bug Analysis

### Current Behavior (Defect)

Verification logic (`evidence_verifier.py`, `tavily_grounder.py`, `deep_analyzer.py`):

1.1 WHEN a claim has entities extracted from the document itself THEN the system marks it VERIFIED via "exact quote in source document", because `_substring_corroboration` checks entities against the same text they came from (circular), so almost every claim passes without external evidence (C1)

1.2 WHEN a Tavily result has relevance_score >= 0.7 and the claim was not escalated to the Super tier THEN the system marks the claim VERIFIED, because `tavily_grounder` hard-codes `supports_claim=True` and relevance only measures topical similarity, not agreement (C2)

1.3 WHEN the Super-tier deep analysis returns `supports_claim` THEN the system copies the raw LLM boolean onto every evidence item, adds a synthetic evidence item scored with the LLM's self-reported confidence, and the verifier turns that into a CONTRADICTED or VERIFIED verdict, so the model effectively has the final say (C3)

1.4 WHEN a claim text contains a valid US-style date such as `12/31/2026` THEN `_is_plausible_date` rejects it (month position > 12) and the claim is marked CONTRADICTED with "Invalid date format detected" (C4)

1.5 WHEN a claim contains a calendar-invalid date such as `02/30/2026`, `2026-02-30`, or the written form "February 30, 2026" THEN the system does not flag it, because only day <= 31 and month <= 12 are checked and written dates are ignored (C4)

1.6 WHEN no claims are extracted THEN the report shows trust_score 100.0 and risk "low", while `compute_trust_score([])` returns 0.0, so the two code paths disagree and an empty or failed extraction looks fully trusted (C5)

Data handling and error handling (`claim_extractor.py`, `model_router.py`, `deep_analyzer.py`, `verify.py`):

1.7 WHEN the model returns valid JSON that is not an object, or a claim item that is not an object, or `confidence` that is not numeric (for example "high"), or `entities` that is not a list of strings THEN the system raises an unhandled `AttributeError`, `ValueError` or `TypeError` and the request fails with HTTP 500 (C6)

1.8 WHEN the model returns a category with different casing (for example "Legal") or an unknown category THEN `should_escalate` silently skips Super-tier analysis and the category is passed through unvalidated (C6)

1.9 WHEN the Nebius call fails, times out, or `NEBIUS_API_KEY` is missing THEN `extract_claims` lets the exception escape and the user receives an opaque HTTP 500 with no actionable message (C7)

1.10 WHEN the deep analyzer returns a non-numeric `confidence` or a string such as "false" for `supports_claim` THEN the Evidence model validation raises outside the try block, or the string is treated as truthy and evidence is flipped to "supports" (C7)

1.11 WHEN Tavily returns a result with `score` null or missing a string THEN `min(max(None, 0.0), 1.0)` raises TypeError, which is only caught by the broad handler and silently drops all evidence for the claim (C7)

Trust boundary and prompt injection (`synthesizer.py`, `verify.py`, `claim_extractor.py`):

1.12 WHEN the Ultra tier returns a summary THEN the raw LLM text is returned to the user unchanged, and it may contradict the deterministic counts or follow instructions injected through document text, violating "never pass raw LLM output to users" (C8)

1.13 WHEN a document contains instructions such as "IGNORE ALL PREVIOUS INSTRUCTIONS" or the filename contains injected text THEN the raw document text, filename, and claim text are interpolated straight into prompts with no delimiting or injection detection, and the challenge case "prompt-injection" has no corresponding detector (C8)

1.14 WHEN an image file is uploaded THEN the system substitutes a placeholder string containing the filename as the "document text", and claims are extracted from that placeholder and may be marked VERIFIED by the circular substring check (C9)

1.15 WHEN the Ultra fallback summary is used THEN it states that claims were "verified against live evidence" even if none had external evidence (C8)

Concurrency and routing (`model_router.py`, `verify.py`):

1.16 WHEN two verification requests run concurrently THEN `reset_usage()` and the module-level `_usage` dict are shared, so one request wipes or pollutes the other's `model_tier_usage` (C10)

1.17 WHEN every Tavily search and Super call runs sequentially for each claim with a 15s search timeout and a 90s model timeout, and the number of claims is unbounded THEN a normal document can exceed the Vercel `maxDuration` of 60s and the request is killed; the 85/10/5 split is also never measured or enforced, and the `super_vl` and `nano_omni` tiers are bucketed inconsistently (C10)

Input handling and API surface (`verify.py`, `challenge.py`, `tavily_grounder.py`, `vercel.json`):

1.18 WHEN a large file is uploaded THEN the full body is read into memory before the size check, and Vercel's request body limit (about 4.5 MB) is below the advertised 20 MB, so large uploads fail with an opaque platform error (C11)

1.19 WHEN an unsupported extension is rejected THEN the "Allowed" list is built from an unordered set, and file type is trusted from the extension alone with no content sniffing (C11)

1.20 WHEN `GET /api/challenges/{id}` is called with an unknown id THEN the system returns HTTP 200 with `{"error": ...}` instead of 404 (C11)

1.21 WHEN Tavily is called THEN the API key is sent in the JSON body and may be logged in error output, instead of an Authorization header (C11)

Packaging, Docker and frontend (`requirements.txt`, `docker-compose.yml`, `frontend/`):

1.22 WHEN dependencies are installed THEN `openai`, `Pillow` and `aiofiles` are listed but unused (the router explicitly avoids the openai SDK), all use open `>=` ranges instead of pinned versions, and the root `requirements.txt` and `backend/requirements.txt` differ (C12)

1.23 WHEN the stack runs through `docker-compose` THEN the frontend container's Vite proxy targets `localhost:8000` (the frontend container itself), `VITE_API_URL` is never read, so API calls fail; the backend image also mounts `./backend` over `/app`, hides installed state, runs as root, and ships `test_pipeline.py` (C13)

1.24 WHEN the frontend calls `/api/challenges` or `/api/challenges/{id}` and the response is not OK or is malformed THEN `ChallengeMode` does not check `response.ok`, an unhandled rejection occurs in `run`, and the user sees nothing (C14)

1.25 WHEN the user switches tabs or resets while a verification request is in flight THEN there is no AbortController, so the late response sets `report` and shows stale results on the wrong tab (C14)

1.26 WHEN a file with an unsupported type or size over 20 MB is dropped THEN `DropZone` does not validate client-side, and the drop area advertises `cursor-pointer` but clicking it does nothing and is not keyboard accessible (C14)

### Expected Behavior (Correct)

2.1 WHEN a claim has entities that appear in the source document THEN the system SHALL NOT treat that as verification, and SHALL only mark a claim VERIFIED from independent external evidence or from deterministic internal-consistency checks, otherwise UNVERIFIABLE (fixes 1.1)

2.2 WHEN Tavily results are returned THEN the system SHALL NOT assume they support the claim, and SHALL set support only from deterministic agreement checks (for example, claim entities, numbers and dates appearing in the result content and no conflicting values), defaulting to neutral/unverifiable when agreement cannot be established (fixes 1.2)

2.3 WHEN Super-tier analysis returns a result THEN the system SHALL treat it as an untrusted advisory claim, validate its schema and types, and SHALL let it produce a CONTRADICTED verdict only if the deterministic verifier can confirm the discrepancy from cited evidence text; the LLM output SHALL NOT directly set a final verdict (fixes 1.3, 1.10)

2.4 WHEN a claim contains a valid date in US, European or ISO format, or in written form THEN the system SHALL accept it, and WHEN the date is calendar-invalid (including February 30, 31 in 30-day months, and non-leap February 29) THEN the system SHALL flag it with a precise reason (fixes 1.4, 1.5)

2.5 WHEN no claims are extracted THEN the system SHALL report a consistent result across all paths (a defined trust_score and risk level that does not imply full verification, and a summary stating that nothing was verified), and `compute_trust_score` SHALL agree with the report (fixes 1.6)

2.6 WHEN the model output is malformed (wrong JSON shape, non-numeric confidence, non-string entities, unknown category) THEN the system SHALL validate and normalize each field (lowercase category from the allowed set, clamp confidence, coerce entities to a list of strings), skip invalid items with a warning, and continue (fixes 1.7, 1.8, 1.11)

2.7 WHEN a model or Tavily call fails, times out, or the API key is missing THEN the system SHALL return a clear, sanitized HTTP error (for example 502 or 503 with a safe message) or degrade gracefully with claims marked UNVERIFIABLE, and SHALL NOT leak internal details or secrets (fixes 1.9)

2.8 WHEN a summary is produced THEN the system SHALL NOT return raw LLM text unvetted; it SHALL prepend or compose a deterministic findings block from verifier counts, SHALL validate the LLM narrative against those counts (reject or replace it on mismatch), and SHALL fall back to a template that makes no claim of live verification unless external evidence exists (fixes 1.12, 1.15)

2.9 WHEN document text, filename or claim text is sent to a model THEN the system SHALL wrap it in clearly delimited untrusted-data blocks, sanitize the filename, detect common injection phrases deterministically and surface them as a flagged finding, and SHALL never let document text change a verdict (fixes 1.13)

2.10 WHEN an image is uploaded THEN the system SHALL either perform real extraction through a configured vision tier or return a clear 422/501 that image analysis is unavailable, and SHALL NOT fabricate claims from a placeholder (fixes 1.14)

2.11 WHEN requests run concurrently THEN the system SHALL track token usage per request (for example via a request-scoped context object or `contextvars`) so one request cannot affect another (fixes 1.16)

2.12 WHEN a document has many claims THEN the system SHALL cap the number of claims, run Tavily lookups concurrently with bounded concurrency, and enforce an overall time budget below the platform limit, returning a partial but honest report; tier usage SHALL be reported consistently per tier with escalation limited to the intended Nano/Super/Ultra proportions (fixes 1.17)

2.13 WHEN a file is uploaded THEN the system SHALL enforce the size limit while streaming (or by `Content-Length`), reject early with 413, align the documented limit with the deployment's real limit, report allowed types in stable order, and check content signatures for PDF and images (fixes 1.18, 1.19)

2.14 WHEN an unknown challenge id is requested THEN the system SHALL return HTTP 404 (fixes 1.20)

2.15 WHEN Tavily is called THEN the system SHALL send the key in an `Authorization: Bearer` header and SHALL ensure it is never logged (fixes 1.21)

2.16 WHEN dependencies are declared THEN the system SHALL list only used packages with pinned versions, and keep root and backend requirement files consistent (fixes 1.22)

2.17 WHEN the stack runs under docker-compose THEN the frontend SHALL reach the backend through a correct proxy target (service name) or `VITE_API_URL`, the backend SHALL run as a non-root user without a source mount that overrides the image in production, and test scripts SHALL be excluded from the image (fixes 1.23)

2.18 WHEN challenge requests fail THEN the frontend SHALL check `response.ok`, show a user-visible error, and avoid unhandled rejections (fixes 1.24)

2.19 WHEN the user switches tab or resets during a request THEN the frontend SHALL abort the in-flight request and ignore its late result (fixes 1.25)

2.20 WHEN a dropped or picked file has an unsupported type or exceeds the size limit THEN the frontend SHALL reject it with a clear message, and the drop area SHALL be operable by keyboard and open the file picker on click (fixes 1.26)

### Unchanged Behavior (Regression Prevention)

3.1 WHEN `evidence_verifier.py` makes a decision THEN the system SHALL CONTINUE TO use only deterministic code with no LLM or network calls

3.2 WHEN a Tavily result with relevance >= 0.7 demonstrably agrees with the claim by deterministic checks THEN the system SHALL CONTINUE TO mark the claim VERIFIED and cite the source URLs

3.3 WHEN evidence demonstrably conflicts with a claim THEN the system SHALL CONTINUE TO mark it CONTRADICTED, checking contradictions before support (fail-safe order)

3.4 WHEN no sufficient evidence exists in either direction THEN the system SHALL CONTINUE TO mark the claim UNVERIFIABLE with a reason that includes the counts and threshold

3.5 WHEN `compute_trust_score` and `compute_risk_level` receive non-empty claim lists THEN the system SHALL CONTINUE TO use the existing formula (double penalty for contradictions, clamped 0 to 100) and thresholds (critical at 3 or more contradictions or score under 30, and so on)

3.6 WHEN tasks are routed THEN the system SHALL CONTINUE TO use Nano for extraction and classification, Super for contradiction detection, and Ultra only once per document for summary generation, with the `TIER_ROUTING` keys unchanged

3.7 WHEN API keys are needed THEN the system SHALL CONTINUE TO read them only from environment variables, with `.env` remaining git-ignored and no secrets committed

3.8 WHEN a valid PDF or UTF-8/latin-1 text file under the size limit is uploaded THEN the system SHALL CONTINUE TO return a `VerificationReport` with the same response schema (`VerificationReport`, `ClaimVerification`, `Claim`, `Evidence` fields unchanged)

3.9 WHEN `GET /health`, `GET /`, and `GET /api/challenges` are called THEN the system SHALL CONTINUE TO return the same response shapes, and known challenge ids SHALL CONTINUE TO return their full document text

3.10 WHEN the app is deployed on Vercel through `api/index.py` THEN the system SHALL CONTINUE TO import `main.app` and serve `/api/*` and `/health` via the existing rewrites

3.11 WHEN the CORS origins list and `CORS_ORIGINS` env var are used THEN the system SHALL CONTINUE TO allow the same default local origins plus configured extras

3.12 WHEN the frontend renders a valid report THEN the system SHALL CONTINUE TO display the scorecard, summary, claim cards, evidence chain, and token telemetry as it does today

## Bug Condition (Derived)

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type PipelineInput  // upload, model output, evidence, request context
  OUTPUT: boolean

  RETURN C1(X) OR C2(X) OR C3(X) OR C4(X) OR C5(X) OR C6(X) OR C7(X)
      OR C8(X) OR C9(X) OR C10(X) OR C11(X) OR C12(X) OR C13(X) OR C14(X)
  // C1  claim verified only via entities taken from the same document
  // C2  Tavily result treated as supporting without agreement check
  // C3  raw LLM verdict feeds the verifier
  // C4  date validation wrong (US dates rejected, impossible dates accepted)
  // C5  empty-claims score/risk inconsistent
  // C6  malformed or unnormalized LLM fields crash or mis-route
  // C7  upstream failure produces opaque 500 or silent drop
  // C8  raw LLM summary or injected text reaches the user
  // C9  image placeholder text used as document
  // C10 shared global usage state, unbounded sequential work
  // C11 upload, API status and secret-handling flaws
  // C12 unused or unpinned dependencies
  // C13 Docker and compose misconfiguration
  // C14 frontend error handling, abort and accessibility gaps
END FUNCTION
```

```pascal
// Property: Fix Checking
FOR ALL X WHERE isBugCondition(X) DO
  result ← verifyflow'(X)
  ASSERT no_crash(result)
     AND verdict_set_only_by_deterministic_verifier(result)
     AND no_unvetted_llm_text_in(result)
     AND valid_dates_not_flagged(result) AND invalid_dates_flagged(result)
     AND usage_isolated_per_request(result)
END FOR
```

```pascal
// Property: Preservation Checking
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT verifyflow(X) = verifyflow'(X)
END FOR
```

Counterexamples demonstrating the bug:
- `_is_plausible_date("12/31/2026")` returns False (should be True).
- `_is_plausible_date("02/30/2026")` returns True (should be False).
- A claim with `entities=["John Smith"]` from a document containing "John Smith" and zero Tavily evidence returns VERIFIED.
- `extract_claims` with model output `{"claims": [{"text": "x", "confidence": "high"}]}` raises ValueError.
- `GET /api/challenges/nope` returns 200 with an error body.
