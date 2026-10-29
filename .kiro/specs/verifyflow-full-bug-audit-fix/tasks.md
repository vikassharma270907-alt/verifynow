# Implementation Plan

## Overview

This plan fixes the 14 defect classes (C1-C14) found in the VerifyFlow audit. Order: exploration tests that fail on unfixed code, preservation tests that pass on unfixed code, fixes grouped by defect class, then a final review by the code-reviewer, security-reviewer and python-reviewer agents.

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1", "2"] },
    { "wave": 2, "tasks": ["3.1", "3.6"] },
    { "wave": 3, "tasks": ["3.2", "3.3", "3.4", "3.5", "3.7", "3.9", "3.10", "3.11"] },
    { "wave": 4, "tasks": ["3.8"] },
    { "wave": 5, "tasks": ["3.12", "3.13"] },
    { "wave": 6, "tasks": ["4"] },
    { "wave": 7, "tasks": ["5.1", "5.2", "5.3"] },
    { "wave": 8, "tasks": ["5.4"] }
  ]
}
```

## Tasks

- [x] 1. Write bug condition exploration tests (one per defect class C1-C14)
  - **Property 1: Bug Condition** - Full Audit Defects C1-C14
  - **CRITICAL**: These tests MUST FAIL on unfixed code - failure confirms the bugs exist
  - **DO NOT attempt to fix the tests or the code when they fail**
  - **NOTE**: These tests encode the expected behavior - they will validate the fixes when they pass after implementation
  - **GOAL**: Surface counterexamples that demonstrate each defect exists
  - **Scoped PBT Approach**: Deterministic defects are scoped to concrete failing cases; use `hypothesis` for date strings (C4), malformed model JSON (C6, C7) and concurrent usage (C10). Mock all `httpx` calls (no live network). Backend: `pytest`, `pytest-asyncio`, `hypothesis` in `backend/tests/`. Frontend: `vitest` and React Testing Library.
  - C1: claim with `entities=["John Smith"]` present in the document and zero external evidence must be UNVERIFIABLE (isBugCondition: entities non-empty AND externalEvidence empty AND originalVerdict = VERIFIED)
  - C2: Tavily result with score 0.82 and no shared tokens with the claim must be UNVERIFIABLE, not VERIFIED
  - C3: mocked Super returning `supports_claim=false` (confidence 0.8) with no confirming verbatim quote must NOT produce CONTRADICTED, and no synthetic evidence item may be appended
  - C4: `12/31/2026` accepted; `02/30/2026`, `2026-02-30`, "February 30, 2026", `02/29/2025` flagged with a precise reason; `02/29/2024` accepted
  - C5: report for zero claims has trust_score and risk equal to `compute_trust_score([])` and `compute_risk_level([])`, and a summary stating nothing was verified
  - C6: `extract_claims` with confidence "high", entities `[1, null]`, category "Legal", list-shaped JSON and non-object items must not raise; `should_escalate` for "Legal" must escalate
  - C7: `httpx.TimeoutException`, missing `NEBIUS_API_KEY`, Tavily `score: null`, and string "false" for `supports_claim` must yield 502/503 with a safe detail or graceful degradation, never an unhandled 500
  - C8: mocked Ultra output with wrong counts or injected text must be replaced; summary starts with a deterministic findings block; fallback makes no "live evidence" claim when no external evidence exists; "IGNORE ALL PREVIOUS INSTRUCTIONS" is surfaced as an injection finding and prompts wrap input in `<untrusted_document_data>`
  - C9: PNG upload must return 501 and never analyze placeholder text
  - C10: two concurrent requests with distinct mocked token counts keep separate `model_tier_usage`; claim count is capped; time budget yields UNVERIFIABLE "Not checked within time budget" for unprocessed claims; `nano_omni` and `super_vl` map to the correct buckets
  - C11: oversized stream returns 413 before full read; wrong-signature PDF returns 400/422; allowed-types list is sorted; unknown challenge id returns 404; Tavily request carries `Authorization: Bearer` and no `api_key` in body
  - C12: static check that requirements are pinned, only used packages are listed, and root and backend files are consistent
  - C13: static check that compose proxy target is not `localhost`, Dockerfile has a `USER`, `.dockerignore` excludes `test_pipeline.py`, `__pycache__`, `.env`
  - C14: failed challenge fetch shows an error, tab switch aborts the in-flight request, bad or oversized file is rejected, Enter/Space on the dropzone opens the picker
  - Run all tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct - it proves the bugs exist)
  - Document counterexamples found (e.g., "`_is_plausible_date('12/31/2026')` returns False", "VERIFIED with empty external evidence", "ValueError on confidence 'high'")
  - Mark task complete when tests are written, run, and failures are documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11, 1.12, 1.13, 1.14, 1.15, 1.16, 1.17, 1.18, 1.19, 1.20, 1.21, 1.22, 1.23, 1.24, 1.25, 1.26_

- [x] 2. Write preservation property tests (BEFORE implementing fixes)
  - **Property 2: Preservation** - Non-Buggy Behavior Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe on UNFIXED code, then write property-based tests for inputs where isBugCondition is false
  - Scoring: for random non-empty status lists, `compute_trust_score` and `compute_risk_level` match the existing formula (double penalty for contradictions, clamp 0-100) and thresholds (critical at 3+ contradictions or score under 30)
  - Bucket logic: for random evidence lists with explicit `supports_claim` and relevance, contradictions are checked first, support at relevance >= 0.7 gives VERIFIED with cited URLs, otherwise UNVERIFIABLE with counts and threshold in the reason
  - Verifier purity: `evidence_verifier.py` imports no LLM, `httpx` or network modules (AST check)
  - Routing: `TIER_ROUTING` keys unchanged; Nano extracts, Super detects contradictions, Ultra summarizes once
  - Secrets: keys read only from env; `.env` is in `.gitignore`
  - Schemas: `VerificationReport`, `ClaimVerification`, `Claim`, `Evidence` field names unchanged; valid PDF and UTF-8/latin-1 text uploads under the limit return a schema-valid report (mocked models)
  - Routes: `GET /health`, `GET /`, `GET /api/challenges` shapes and known challenge ids return full text
  - Deployment: `api/index.py` imports `main.app`; `vercel.json` rewrites for `/api/*` and `/health` exist; CORS defaults and `CORS_ORIGINS` behavior unchanged
  - Valid dates already accepted today (e.g. `2026-03-15`, `15/03/2026`) stay accepted
  - Frontend: snapshot of a valid report renders scorecard, summary, claim cards, evidence chain and telemetry
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12_

- [ ] 3. Fix for VerifyFlow full bug audit (C1-C14)

  - [x] 3.1 Create the pure deterministic helper module (foundation for C2, C4, C6, C8)
    - Add `backend/services/claim_checks.py` with no network, LLM or file I/O
    - `parse_dates` and `validate_date` build real `datetime.date` values for ISO, slash/dash numeric (accept if valid in US or European order) and written forms; return `(ok, reason)` such as "February 30 does not exist" or "2025 is not a leap year"
    - `extract_numbers` normalizes commas and currency; `agreement(claim, content)` returns `supports`, `conflicts` or `neutral`
    - `detect_injection(text)` regex list returning matched phrases (never changes a verdict); `sanitize_filename`; `normalize_category` mapping to `{legal, financial, identity, temporal, regulatory, factual}` with `factual` default
    - _Bug_Condition: isBugCondition(X) where C2, C4, C6, C8 apply_
    - _Expected_Behavior: expectedBehavior(result) from design (Properties 2, 3, 4)_
    - _Preservation: valid dates and genuine support or conflict still classified correctly_
    - _Requirements: 2.2, 2.4, 2.6, 2.9, 3.1_

  - [x] 3.2 Fix C1, C4, C5: evidence verifier (`backend/services/evidence_verifier.py`)
    - Remove `_substring_corroboration` as a VERIFIED path
    - `_pattern_check` and `_is_plausible_date` use `claim_checks.validate_date`; calendar-invalid dates give CONTRADICTED with the precise reason; valid dates alone add no verdict
    - Keep 0.7 thresholds and contradiction-first order; keep UNVERIFIABLE reason with counts and threshold
    - Add shared empty-report constants so `compute_trust_score([])`, `compute_risk_level([])` and the report agree and do not imply verification
    - Import only `claim_checks`, models and stdlib; introduce no LLM or network calls
    - _Bug_Condition: isBugCondition(X) where C1, C4, C5_
    - _Expected_Behavior: VERIFIED only with agreeing external evidence; dates match the calendar; empty report consistent_
    - _Preservation: scoring formula and thresholds for non-empty lists; fail-safe order; purity_
    - _Requirements: 2.1, 2.4, 2.5, 3.1, 3.3, 3.4, 3.5_

  - [x] 3.3 Fix C2, C7, C11 (Tavily): grounder (`backend/services/tavily_grounder.py`)
    - Replace hard-coded `supports_claim=True` with the `agreement` result; `neutral` sets `supports_claim=False` and caps relevance at `NEUTRAL_RELEVANCE_CAP = 0.69`; `conflicts` keeps the real score with `supports_claim=False`
    - Coerce `score` (None or non-numeric becomes 0.0) and `url`, `title`, `content` to strings
    - Send `Authorization: Bearer <key>`, remove `api_key` from the body, log only status codes and truncated bodies that cannot contain the key
    - Keep `search_evidence_for_claim` independent so it can run under a semaphore
    - _Bug_Condition: isBugCondition(X) where C2, C7, C11 (Tavily key)_
    - _Expected_Behavior: support set only by deterministic agreement; null scores handled; key in header_
    - _Preservation: agreeing results with relevance >= 0.7 still yield VERIFIED with cited URLs_
    - _Requirements: 2.2, 2.6, 2.15, 3.2_

  - [x] 3.4 Fix C3, C6, C7, C8 (Super tier): deep analyzer (`backend/services/deep_analyzer.py`)
    - Schema-validate output: real booleans only (parse "false" and "true" strings explicitly), clamp confidence, strings for `reasoning` and `cited_quote`; invalid output returns evidence unchanged
    - Advisory only: stop mutating `supports_claim` on every item and stop appending synthetic evidence; flip a single item only when `cited_quote` is a verbatim substring of that item's content AND `agreement` returns `conflicts`
    - Wrap claim and evidence in `<untrusted_document_data>` blocks with a data-only instruction
    - `should_escalate` uses `normalize_category`
    - _Bug_Condition: isBugCondition(X) where C3, C6, C7, C8_
    - _Expected_Behavior: LLM output never directly sets a verdict_
    - _Preservation: Super still used for contradiction detection on eligible categories_
    - _Requirements: 2.3, 2.6, 2.9, 3.6_

  - [x] 3.5 Fix C6, C7, C8 (Nano): claim extractor (`backend/services/claim_extractor.py`)
    - Require `data` to be an object and `claims` a list; per item require an object with non-empty string `text`; safe-float confidence (default 0.5, clamp 0-1); keep only string entities; normalize category; skip bad items with a warning
    - Catch upstream errors and raise typed `UpstreamError`
    - Wrap the document in `<untrusted_document_data>` and state in the system prompt that it is data, never instructions
    - _Bug_Condition: isBugCondition(X) where C6, C7, C8_
    - _Expected_Behavior: malformed output normalized or skipped, request continues_
    - _Preservation: well-formed output yields the same Claim objects_
    - _Requirements: 2.6, 2.7, 2.9, 3.6, 3.8_

  - [x] 3.6 Fix C7, C10: model router (`backend/services/model_router.py`)
    - Replace module-level `_usage` with `ContextVar[UsageTracker]`; add `start_request_usage()`; `get_usage()` reads the request tracker
    - Map `nano` and `nano_omni` to the nano bucket, `super` and `super_vl` to the super bucket; unknown tiers log a warning
    - Wrap `httpx` errors into `UpstreamError(status, safe_message)` that never includes the Authorization header or key; missing `NEBIUS_API_KEY` maps to 503
    - Expose a Super-call counter so `verify.py` can cap escalation near 10 percent of claims (rounded up, minimum one when eligible) and report the measured split
    - Keep `TIER_ROUTING` keys unchanged
    - _Bug_Condition: isBugCondition(X) where C7, C10_
    - _Expected_Behavior: per-request usage isolation; sanitized upstream errors_
    - _Preservation: TIER_ROUTING keys and model assignments unchanged; env-only keys_
    - _Requirements: 2.7, 2.11, 2.12, 3.6, 3.7_

  - [x] 3.7 Fix C8: synthesizer (`backend/services/synthesizer.py`)
    - Build a deterministic findings block from verifier counts, risk, and any injection or date findings; always place it first
    - Accept the LLM narrative only if every integer count matches the verifier counts and it claims no verification when `verified == 0`; otherwise use the template
    - Honest fallback: states verified-with-external-evidence versus not-verified counts; says "live evidence" only when at least one claim cites external sources
    - Put sanitized filename and claim text inside untrusted-data tags
    - _Bug_Condition: isBugCondition(X) where C8_
    - _Expected_Behavior: no unvetted LLM text reaches users_
    - _Preservation: Ultra still called once per document_
    - _Requirements: 2.5, 2.8, 2.9, 3.6_

  - [x] 3.8 Fix C5, C7, C8, C9, C10, C11: verify router (`backend/routers/verify.py`)
    - Call `start_request_usage()` instead of `reset_usage()`
    - Reject early on `Content-Length` above the limit; read in chunks and stop at the limit with 413; align `MAX_UPLOAD_SIZE_MB` with the deployment limit (about 4 MB on Vercel)
    - Sorted allowed-types list; check `%PDF-` and PNG, JPEG and WEBP magic bytes; mismatch gives 400 or 422
    - Images return 501 "Image analysis is not available" unless a vision tier is configured; never analyze placeholder text
    - Cap claims (e.g. 25), bound Tavily and Super calls with `asyncio.Semaphore`, enforce a deadline (e.g. 45s) and mark unprocessed claims UNVERIFIABLE "Not checked within time budget"
    - Empty-claims report uses shared constants and a summary stating nothing was verified
    - Run `detect_injection` on document and filename; surface in the findings block; pass sanitized filename downstream
    - Catch `UpstreamError` and return its status and safe detail
    - _Bug_Condition: isBugCondition(X) where C5, C7, C8, C9, C10, C11_
    - _Expected_Behavior: bounded, isolated, honest reports and sanitized errors_
    - _Preservation: valid PDF and text uploads under the limit return the same VerificationReport schema_
    - _Requirements: 2.5, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12, 2.13, 3.8_

  - [x] 3.9 Fix C11: challenge router (`backend/routers/challenge.py`)
    - Raise `HTTPException(404)` for unknown challenge ids; leave the list route and known ids unchanged
    - _Bug_Condition: isBugCondition(X) where C11 (unknown id)_
    - _Expected_Behavior: HTTP 404_
    - _Preservation: `GET /api/challenges` and known ids return the same shapes_
    - _Requirements: 2.14, 3.9_

  - [-] 3.10 Fix C11, C12, C13: packaging, Docker and Vercel config
    - Remove `openai`, `Pillow`, `aiofiles` unless an import is found; pin exact versions; make root `requirements.txt` consistent with `backend/requirements.txt`; move `pytest`, `hypothesis`, `pytest-asyncio` into a separate dev requirements file
    - Dockerfile: non-root `USER`; `docker-compose.yml`: no source bind mount for the default service (optional dev override file); add `.dockerignore` excluding `test_pipeline.py`, `__pycache__`, `.env`
    - Vite proxy target from `VITE_API_URL` or `http://backend:8000`
    - `vercel.json`: document the real body limit and keep `api/index.py` rewrites working
    - _Bug_Condition: isBugCondition(X) where C11, C12, C13_
    - _Expected_Behavior: pinned minimal deps; compose frontend reaches backend; non-root image_
    - _Preservation: `api/index.py` still imports `main.app`; CORS config unchanged_
    - _Requirements: 2.13, 2.16, 2.17, 3.7, 3.10, 3.11_

  - [~] 3.11 Fix C14: frontend (`frontend/src/components/ChallengeMode.*`, `DropZone.*`, `App.*`)
    - Check `response.ok` for challenge list, detail and run; catch errors and show a visible message
    - Hold an `AbortController` in a ref; abort on tab switch, reset and unmount; ignore `AbortError` and late results
    - DropZone: validate extension and size (20 MB or the configured limit) before upload with a visible message; make it a focusable `role="button"` with `tabIndex=0`, Enter and Space handling, and a hidden file input opened on click
    - _Bug_Condition: isBugCondition(X) where C14_
    - _Expected_Behavior: errors shown, stale requests aborted, files validated, keyboard operable_
    - _Preservation: valid reports render exactly as before_
    - _Requirements: 2.18, 2.19, 2.20, 3.12_

  - [~] 3.12 Verify bug condition exploration tests now pass
    - **Property 1: Expected Behavior** - Full Audit Defects C1-C14 Fixed
    - **IMPORTANT**: Re-run the SAME tests from task 1 - do NOT write new tests
    - The tests from task 1 encode the expected behavior
    - Run backend (`pytest`) and frontend (`vitest --run`) exploration tests from task 1
    - **EXPECTED OUTCOME**: Tests PASS (confirms C1-C14 are fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12, 2.13, 2.14, 2.15, 2.16, 2.17, 2.18, 2.19, 2.20_

  - [~] 3.13 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Buggy Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from task 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after the fixes

- [~] 4. Checkpoint - Ensure all tests pass
  - Run the full backend suite (`pytest`), the frontend suite (`vitest --run`), and the frontend build
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Final review gate with reviewer agents
  - [~] 5.1 Run the code-reviewer agent on all changed files
    - Review backend, frontend and config diffs for quality, maintainability and adherence to project rules (deterministic verifier, 85/10/5 routing, no raw LLM output)
    - Fix all CRITICAL and HIGH findings, then re-run tests
    - _Requirements: 2.1, 2.8, 3.1, 3.6_

  - [~] 5.2 Run the security-reviewer agent on all changed files
    - Focus on upload handling (size, signatures), prompt injection, secret handling (Tavily header, no key in logs or errors), error sanitization, Docker non-root and CORS
    - Fix all CRITICAL and HIGH findings, then re-run tests
    - _Requirements: 2.7, 2.9, 2.13, 2.15, 2.17, 3.7, 3.11_

  - [~] 5.3 Run the python-reviewer agent on all changed Python files
    - Check PEP 8, type hints, async correctness (`contextvars`, semaphore, deadline), exception handling and test quality
    - Fix all CRITICAL and HIGH findings, then re-run tests
    - _Requirements: 2.3, 2.6, 2.11, 2.12_

  - [~] 5.4 Final confirmation
    - Re-run the full test suites after review fixes
    - Ensure all tests pass, ask the user if questions arise.

## Notes

- `evidence_verifier.py` must stay deterministic: no LLM, network or model_router imports.
- Tasks 1 and 2 run against UNFIXED code. Task 1 must fail and task 2 must pass before any fix starts.
- Tests mock all `httpx` calls; no live Nebius or Tavily requests.
- Do not change response schemas (`VerificationReport`, `ClaimVerification`, `Claim`, `Evidence`).
- Run frontend tests with `vitest --run`; do not start dev servers from the agent.
