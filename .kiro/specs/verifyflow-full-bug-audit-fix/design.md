# VerifyFlow Full Bug Audit Fix Bugfix Design

## Overview

VerifyFlow promises that "the model can think, but it does not get the final say; the evidence does." The audit found 14 defect classes (C1 to C14) that break that promise or make the app unreliable. The worst ones let claims reach VERIFIED without external corroboration (C1, C2), let an LLM boolean drive the verdict (C3), and show unchecked LLM text to users (C8). Others reject valid dates (C4), crash on malformed model output (C6, C7), share usage state across requests (C10), mishandle uploads and secrets (C9, C11), and break Docker and the frontend (C12 to C14).

The fix strategy is minimal and layered:

1. Keep `evidence_verifier.py` deterministic and the only place that sets a verdict. Remove the circular document check and make "support" something the code computes, not something assumed or copied from a model.
2. Add one small pure module of deterministic checks (dates, numbers, entity agreement, injection phrases) that both the grounder and the verifier can import. It makes no network or LLM calls.
3. Treat every LLM output as untrusted input: validate and normalize at the boundary, degrade to UNVERIFIABLE on failure, and never forward model prose without a deterministic findings block.
4. Make request state explicit (`contextvars`), bound the work (claim cap, bounded concurrency, time budget), and harden upload and error handling.
5. Fix packaging, Docker and frontend behavior without changing any response schema.

Public schemas (`VerificationReport`, `ClaimVerification`, `Claim`, `Evidence`) stay unchanged. "Neutral" evidence is expressed with the existing fields by capping its `relevance_score` below the 0.7 thresholds, so it falls into neither the supporting nor the contradicting bucket.

## Glossary

- **Bug_Condition (C)**: The union C1 to C14 defined in `bugfix.md`. `isBugCondition(X)` is true when any class applies to the pipeline input X.
- **Property (P)**: The desired behavior for inputs where C holds: no crash, verdict set only by the deterministic verifier, no unvetted LLM text, correct dates, per-request isolation.
- **Preservation**: Behavior for inputs where C does not hold that must stay identical (clauses 3.1 to 3.12).
- **verify_claim**: Function in `backend/services/evidence_verifier.py` that applies deterministic rules and sets `claim.status`.
- **Neutral evidence**: An `Evidence` item whose relevance is capped at `NEUTRAL_RELEVANCE_CAP` (0.69) so the verifier ignores it for both support and contradiction.
- **Agreement check**: Deterministic comparison of the claim's numbers, dates and entities against evidence content, returning `supports`, `conflicts` or `neutral`.
- **Advisory**: A schema-validated Super-tier result that cannot set a verdict. It may only point at a verbatim quote that the deterministic check then confirms or ignores.
- **Findings block**: Deterministic summary text built from verifier counts and flagged findings, always placed before any LLM narrative.
- **UsageTracker**: Request-scoped token counter stored in a `ContextVar`, replacing the module-level `_usage` dict.
- **Time budget**: Total seconds a request may spend before remaining claims are returned as UNVERIFIABLE with a "not checked in time" reason.

## Bug Details

### Bug Condition

The bug manifests whenever one of the 14 defect classes is triggered. Each class has a distinct trigger and a distinct location:

| Class | Location | Trigger |
|-------|----------|---------|
| C1 | `evidence_verifier._substring_corroboration` | Entities checked against the text they were extracted from |
| C2 | `tavily_grounder` | `supports_claim=True` hard-coded, relevance read as agreement |
| C3 | `deep_analyzer.analyze_claim_evidence` | Raw LLM boolean copied to all evidence plus synthetic evidence scored by LLM confidence |
| C4 | `evidence_verifier._is_plausible_date` | US dates rejected, calendar-invalid dates accepted, written dates ignored |
| C5 | `verify.py` vs `compute_trust_score` | Empty claims give 100.0 / low vs 0.0 |
| C6 | `claim_extractor`, `deep_analyzer.should_escalate` | Wrong JSON shapes, non-numeric confidence, category casing |
| C7 | `claim_extractor`, `model_router`, `deep_analyzer`, `tavily_grounder` | Upstream failure or bad types produce 500 or silent drop |
| C8 | `synthesizer`, `claim_extractor`, `verify.py` | Raw LLM summary shown; document text and filename interpolated into prompts; fallback overclaims |
| C9 | `verify._extract_text` | Image placeholder treated as document text |
| C10 | `model_router._usage`, `verify.py` loop | Global usage state, sequential unbounded work |
| C11 | `verify.py`, `challenge.py`, `tavily_grounder`, `vercel.json` | Read-then-check upload size, unordered allow list, 200 on unknown id, key in body |
| C12 | `requirements.txt` files | Unused, unpinned, inconsistent dependencies |
| C13 | `Dockerfile`, `docker-compose.yml`, Vite config | Proxy to wrong host, source mount, root user |
| C14 | `frontend/` | Missing `response.ok` checks, no abort, no upload validation or keyboard support |

**Formal Specification:**
```
FUNCTION isBugCondition(X)
  INPUT: X of type PipelineInput  // upload, model output, evidence, request context
  OUTPUT: boolean

  RETURN
    (X.claim.entities NOT EMPTY AND X.externalEvidence IS EMPTY
       AND originalVerdict(X) = VERIFIED)                                  // C1
    OR (X.tavilyResult.relevance >= 0.7 AND NOT agrees(X.claim, X.tavilyResult)
       AND originalVerdict(X) = VERIFIED)                                  // C2
    OR (X.superResult EXISTS AND originalVerdict(X) DEPENDS ON X.superResult.supports_claim) // C3
    OR (X.claim.containsDate AND dateJudgedWrong(X.claim))                 // C4
    OR (X.claims IS EMPTY AND reportScore(X) != compute_trust_score([]))   // C5
    OR (X.modelJson IS malformed OR X.category NOT IN canonical)           // C6
    OR (X.upstreamCall FAILS OR X.fieldTypes INVALID)                      // C7
    OR (X.summary IS raw LLM text OR X.promptInput IS undelimited)         // C8
    OR (X.file.isImage AND textIsPlaceholder(X))                           // C9
    OR (X.concurrentRequests > 1 OR X.claims.count UNBOUNDED)              // C10
    OR (X.upload.exceedsLimit OR X.challengeId UNKNOWN OR X.tavilyKeyInBody) // C11
    OR (X.requirements UNUSED OR UNPINNED OR INCONSISTENT)                 // C12
    OR (X.runtime = DockerCompose AND misconfigured)                       // C13
    OR (X.frontendEvent IN {badResponse, tabSwitch, badFile, keyboard})    // C14
END FUNCTION
```

### Examples

- `_is_plausible_date("12/31/2026")` returns False. Expected: accepted. Actual: claim CONTRADICTED with "Invalid date format detected".
- `_is_plausible_date("02/30/2026")` returns True. Expected: flagged "February has at most 28/29 days". Actual: passes.
- A claim `entities=["John Smith"]` from a document that contains "John Smith", with zero Tavily evidence, returns VERIFIED "exact quote in source document". Expected: UNVERIFIABLE.
- A Tavily result about an unrelated company with `score=0.82` marks the claim VERIFIED because `supports_claim=True`. Expected: neutral, so UNVERIFIABLE.
- Super says `supports_claim=false` with confidence 0.8. Actual: CONTRADICTED from a synthetic evidence item. Expected: CONTRADICTED only if a cited quote in the evidence text deterministically conflicts with the claim.
- Model returns `{"claims":[{"text":"x","confidence":"high"}]}`. Actual: `ValueError` and HTTP 500. Expected: item normalized (confidence default 0.5) or skipped, request continues.
- Model returns category `"Legal"`. Actual: Super tier skipped. Expected: normalized to `legal` and escalated.
- `GET /api/challenges/nope` returns 200 with an error body. Expected: 404.
- Document says "IGNORE ALL PREVIOUS INSTRUCTIONS". Expected: delimited in the prompt, and a deterministic "possible prompt injection" finding is surfaced.
- Zero claims extracted. Actual: score 100.0, risk "low". Expected: consistent defined result that does not imply verification.
- Edge case: `02/29/2024` (leap year) is valid and must not be flagged; `02/29/2025` must be flagged.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- `evidence_verifier.py` stays pure code: no LLM, no network (3.1).
- A Tavily result with relevance >= 0.7 that deterministically agrees still gives VERIFIED with cited URLs (3.2).
- Contradictions are checked before support (3.3).
- Insufficient evidence still gives UNVERIFIABLE with counts and threshold in the reason (3.4).
- `compute_trust_score` and `compute_risk_level` keep their formula and thresholds for non-empty lists (3.5).
- Nano extracts and classifies, Super detects contradictions, Ultra summarizes once; `TIER_ROUTING` keys unchanged (3.6).
- Keys come only from environment variables; `.env` stays git-ignored (3.7).
- Valid PDF and UTF-8/latin-1 text uploads return the same `VerificationReport` schema (3.8).
- `GET /health`, `GET /`, `GET /api/challenges` and known challenge ids keep their shapes (3.9).
- `api/index.py` still imports `main.app` and Vercel rewrites keep working (3.10).
- CORS defaults and `CORS_ORIGINS` behavior unchanged (3.11).
- Frontend renders valid reports as today (3.12).

**Scope:**
All inputs where `isBugCondition` is false must behave identically. This includes:
- Well-formed model output with canonical categories and numeric confidences
- Valid dates in any accepted format
- Evidence that truly supports or contradicts a claim
- Valid uploads under the size limit
- Non-empty claim lists scored by the existing formula

## Hypothesized Root Cause

1. **Trust shortcuts added for demo speed (C1, C2, C3)**: The substring rule, the hard-coded `supports_claim=True`, and copying the LLM boolean were convenience paths. They treat topical relevance or model opinion as agreement.
   - The verifier has no agreement signal other than the boolean it is given.
   - `supports_claim` is a bool with no neutral state, so unknown cases were forced to True.

2. **Naive date logic (C4)**: One heuristic assumes day-first order, never builds a real `date`, and ignores written months.

3. **Missing boundary validation (C6, C7)**: `json.loads` results are used with `.get` and `float()` directly, the Evidence model is built outside the `try`, and `call_model` re-raises raw exceptions that the router layer never maps to HTTP errors.

4. **Output trusted as final (C8, C9)**: The synthesizer returns model text verbatim and the fallback string states a fact not computed from evidence. The image branch was a stub left in the main path.

5. **Module-level mutable state and unbounded loops (C10)**: `_usage` is a global reset per request. The claim loop awaits search and Super calls one by one with no cap or deadline, against a 60s Vercel limit.

6. **Upload and API shortcuts (C11)**: `await file.read()` precedes the size check, extension is the only type check, the challenge route returns a dict, and Tavily follows its older body-key style.

7. **Config drift (C12, C13, C14)**: Requirements were not pruned after dropping the openai SDK. Compose reuses a dev setup (bind mount, `localhost` proxy). The frontend has the happy path only.

## Correctness Properties

Property 1: Bug Condition - Verdicts come only from deterministic evidence checks

_For any_ claim and evidence set where the bug condition holds for C1, C2 or C3 (circular document match, unconfirmed Tavily relevance, or an LLM-supplied verdict), the fixed `verify_claim` SHALL return VERIFIED only when at least one external evidence item deterministically agrees with the claim, SHALL return CONTRADICTED only when a deterministic conflict is found in cited evidence text, and SHALL otherwise return UNVERIFIABLE; no LLM field SHALL directly set the status.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Bug Condition - Date validation matches the calendar

_For any_ date string in US (`MM/DD/YYYY`), European (`DD/MM/YYYY`), ISO (`YYYY-MM-DD`) or written ("February 3, 2026") form, the fixed date validator SHALL accept it if and only if it names a real calendar date (including leap-year handling), and SHALL return a precise reason when it does not; an ambiguous slash date SHALL be accepted if it is valid under at least one of the US or European readings.

**Validates: Requirements 2.4**

Property 3: Bug Condition - Malformed model and upstream output never crash the request

_For any_ model or Tavily output (wrong JSON shape, non-object items, non-numeric or out-of-range confidence, non-string entities, unknown or mixed-case category, null scores, string booleans, timeouts, missing keys), the fixed pipeline SHALL normalize or skip the offending item and complete, or SHALL return a sanitized 502/503 error for a hard upstream failure, and SHALL never raise an unhandled exception or leak secrets.

**Validates: Requirements 2.6, 2.7**

Property 4: Bug Condition - No unvetted LLM text and no document-controlled behavior

_For any_ report produced by the fixed pipeline, the `summary` SHALL begin with a deterministic findings block whose counts equal the verifier counts, SHALL include the LLM narrative only if it passes validation against those counts, SHALL NOT claim live verification unless external evidence exists, and SHALL be unaffected in verdicts by injected instructions in the document, filename or claim text. An empty-claims report SHALL agree with `compute_trust_score([])`, and an image upload SHALL never be analyzed from placeholder text.

**Validates: Requirements 2.5, 2.8, 2.9, 2.10**

Property 5: Bug Condition - Requests are isolated and bounded

_For any_ set of concurrent verification requests, each report's `model_tier_usage` SHALL equal the tokens consumed by that request alone, and for any document the request SHALL process at most the configured maximum number of claims within the time budget, returning a partial but honest report when the budget is exhausted.

**Validates: Requirements 2.11, 2.12**

Property 6: Bug Condition - API, packaging and frontend hardening

_For any_ upload, challenge id, dependency set, compose run and frontend event in the C11 to C14 classes, the fixed system SHALL reject oversized or wrong-signature uploads with 413/400/422 before full buffering, return 404 for unknown challenge ids, send the Tavily key in an Authorization header, declare only used pinned dependencies, route the frontend to the backend service in compose, and have the UI show errors, abort stale requests, validate dropped files and support keyboard operation.

**Validates: Requirements 2.13, 2.14, 2.15, 2.16, 2.17, 2.18, 2.19, 2.20**

Property 7: Preservation - Non-buggy inputs behave as before

_For any_ input where the bug condition does NOT hold (well-formed model output, valid dates, genuinely agreeing or conflicting evidence, valid uploads, non-empty claim lists), the fixed code SHALL produce the same verdict, trust score, risk level, response schema, routing and HTTP shapes as the original code, preserving the deterministic-only verifier, fail-safe contradiction ordering, existing scoring formula and thresholds, and unchanged endpoints.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12**

## Fix Implementation

### Changes Required

Assuming the root cause analysis is correct:

**File**: `backend/services/claim_checks.py` (new, pure, no I/O)

**Functions**: `parse_dates`, `validate_date`, `extract_numbers`, `agreement(claim, content)`, `detect_injection(text)`, `sanitize_filename`, `normalize_category`

**Specific Changes**:
1. **Real date validation (C4)**: Build dates with `datetime.date`. Parse ISO, slash/dash numeric (try US and European orders; accept if either is valid), and written forms ("Feb 3, 2026", "3 February 2026"). Return `(ok, reason)` with reasons such as "February 30 does not exist" or "2025 is not a leap year".
2. **Agreement check (C2)**: Compare claim numbers, dates and entities with evidence content after normalization (strip commas and currency, case-fold). Return `supports` when at least half of the claim's checkable tokens (minimum one) appear in the evidence and no checkable value conflicts; `conflicts` when the same entity or label appears with a different number or date; otherwise `neutral`.
3. **Injection detection (C8)**: Case-insensitive regex list ("ignore (all )?previous instructions", "system prompt", "you are now", role-switch markers). Returns matched phrases for a finding; it never changes a verdict.
4. **Normalizers (C6)**: `normalize_category` lowercases and maps to `{legal, financial, identity, temporal, regulatory, factual}` with `factual` as the default.

**File**: `backend/services/evidence_verifier.py`

**Function**: `verify_claim`, `_pattern_check`, `_is_plausible_date`, `compute_trust_score`

**Specific Changes**:
1. **Remove circular rule (C1)**: Delete `_substring_corroboration` as a VERIFIED path. A document-internal match is never a verification.
2. **Keep bucket logic, change the inputs (C2, C3)**: Supporting and contradicting buckets still use the 0.7 thresholds, but now rely on `supports_claim` values the grounder computed from the agreement check. Contradictions are still checked first (3.3).
3. **Internal consistency checks (C1, C4)**: `_pattern_check` uses `claim_checks.validate_date`. Calendar-invalid dates give CONTRADICTED with the precise reason. Valid dates add no verdict by themselves (stays UNVERIFIABLE unless evidence agrees).
4. **Empty-claims consistency (C5)**: Add shared constants for the empty-report trust score and risk level so the report and `compute_trust_score([])` agree and do not imply verification. Exact values are an implementation choice.
5. **No new imports of network or model code**: The module imports only `claim_checks`, models and stdlib (3.1). A test asserts this.

**File**: `backend/services/tavily_grounder.py`

**Function**: `search_evidence_for_claim`

**Specific Changes**:
1. **Compute support (C2)**: Replace `supports_claim=True` with the result of `agreement`. For `neutral`, set `supports_claim=False` and cap `relevance_score` at `NEUTRAL_RELEVANCE_CAP = 0.69` so it is ignored by both buckets. For `conflicts`, keep the real score with `supports_claim=False`.
2. **Safe parsing (C7)**: Coerce `score` with a helper (`None` or non-numeric becomes 0.0), coerce `url`, `title`, `content` to strings.
3. **Auth header (C11)**: Send `Authorization: Bearer <key>` and remove `api_key` from the body. Log only status codes and truncated bodies that cannot contain the key.
4. **Concurrency hook**: Keep the function independent so `verify.py` can call it under a semaphore.

**File**: `backend/services/deep_analyzer.py`

**Function**: `should_escalate`, `analyze_claim_evidence`

**Specific Changes**:
1. **Schema-validate (C3, C7)**: Parse into a small validator: `supports_claim` accepts only real booleans (strings like "false" are parsed explicitly), `confidence` is clamped, `reasoning` and `cited_quote` are strings. Invalid output returns the evidence unchanged.
2. **Advisory only (C3)**: Do not mutate `supports_claim` on every item and do not append synthetic evidence. If the advisory says contradicted and `cited_quote` is a verbatim substring of an evidence item's content, run the deterministic `agreement` check on that item; only a `conflicts` result flips that single item to `supports_claim=False`.
3. **Delimited prompt (C8)**: Wrap claim and evidence in `<untrusted_document_data>` blocks with an instruction to treat them as data.
4. **Case-insensitive routing (C6)**: `should_escalate` uses `normalize_category`.

**File**: `backend/services/claim_extractor.py`

**Function**: `extract_claims`

**Specific Changes**:
1. **Item-level validation (C6)**: Require `data` to be an object and `claims` a list. Per item, require an object with non-empty string `text`; coerce confidence via a safe float (default 0.5, clamp 0 to 1); keep only string entities; normalize category. Skip bad items with a warning.
2. **Failure mapping (C7)**: Catch upstream errors and raise a typed `UpstreamError` that the router maps to 502 or 503 with a safe message. A missing `NEBIUS_API_KEY` maps to 503.
3. **Delimited prompt (C8)**: Wrap the document in `<untrusted_document_data>` tags; the system prompt states that content inside is data and never instructions.

**File**: `backend/services/model_router.py`

**Function**: `call_model`, `get_usage`, `reset_usage`

**Specific Changes**:
1. **Request-scoped usage (C10)**: Replace `_usage` with a `ContextVar[UsageTracker]`. `start_request_usage()` returns a fresh tracker for the request task; `get_usage()` reads it. Per-request context propagates to child tasks created inside the request.
2. **Consistent buckets (C10)**: Map `nano` and `nano_omni` to the nano bucket and `super` and `super_vl` to the super bucket explicitly; unknown tiers log a warning instead of silently landing in super.
3. **Typed errors (C7)**: Wrap `httpx` errors into `UpstreamError(status, safe_message)` and never include the Authorization header or key.
4. **Escalation budget (C10)**: Expose a counter so `verify.py` can cap Super calls at roughly 10 percent of claims (rounded up, minimum one when eligible) and report the measured split.

**File**: `backend/services/synthesizer.py`

**Function**: `generate_summary`, `_fallback_summary`

**Specific Changes**:
1. **Findings block (C8)**: Build a deterministic block from counts, risk and any injection or date findings. It is always first in the summary.
2. **Validate narrative (C8)**: Accept the LLM narrative only if every integer count it states matches the verifier counts and it contains no claim of verification when `verified == 0`; otherwise drop it and use the template.
3. **Honest fallback (C8)**: Fallback text says how many claims were verified with external evidence, how many were not, and does not say "live evidence" unless at least one claim cites external sources.
4. **Delimit inputs (C8)**: Sanitized filename and claim text go inside untrusted-data tags.

**File**: `backend/routers/verify.py`

**Function**: `verify_document`, `_extract_text`

**Specific Changes**:
1. **Streaming size check (C11)**: Reject early on `Content-Length` above the limit, then read in chunks and stop at the limit with 413. Align `MAX_UPLOAD_SIZE_MB` to the deployment limit (about 4 MB on Vercel, larger elsewhere via config).
2. **Ordered allow list and signatures (C11)**: Sort the allowed list; check `%PDF-` for PDFs and magic bytes for PNG, JPEG and WEBP; mismatches give 400 or 422.
3. **Images (C9)**: Return 501 "Image analysis is not available" unless a vision tier is configured. No placeholder text is ever analyzed.
4. **Request usage (C10)**: Call `start_request_usage()` at the top instead of `reset_usage()`.
5. **Bounded pipeline (C10)**: Cap claims (for example 25), use `asyncio.Semaphore` for Tavily and Super calls, and wrap the loop with a deadline (for example 45s). Claims not processed in time are marked UNVERIFIABLE with reason "Not checked within time budget".
6. **Empty report (C5)**: Use the shared constants and a summary that says nothing was verified.
7. **Injection finding (C8)**: Run `detect_injection` on the document and filename; include the finding in the findings block and pass a sanitized filename downstream.
8. **Error mapping (C7)**: Catch `UpstreamError` and return its status and safe detail.

**File**: `backend/routers/challenge.py`

1. **404 for unknown id (C11)**: Raise `HTTPException(404)`; known ids and the list route are unchanged (3.9).

**Files**: `requirements.txt`, `backend/requirements.txt`, `Dockerfile`, `docker-compose.yml`, `frontend/vite.config.*`, `.dockerignore`, `vercel.json`

1. **Dependencies (C12)**: Remove `openai`, `Pillow`, `aiofiles` unless an import is found; pin exact versions; make the root file reference `backend/requirements.txt` or match it. Put `pytest`, `hypothesis`, `pytest-asyncio` in a separate dev requirements file.
2. **Docker (C13)**: Non-root user, no source bind mount for the default service (optional dev override file), `.dockerignore` excludes `test_pipeline.py`, `__pycache__`, `.env`. Vite proxy target comes from `VITE_API_URL` or `http://backend:8000`.
3. **Vercel (C11)**: Document the real body limit and set the app limit to match.

**Files**: `frontend/src/components/ChallengeMode.*`, `DropZone.*`, `App.*`

1. **Response checks (C14)**: Check `response.ok`, catch and show an error message for challenge list, detail and run.
2. **Abort (C14)**: Hold an `AbortController` in a ref; abort on tab switch, reset and unmount; ignore `AbortError`.
3. **DropZone (C14)**: Validate extension and size limit before upload with a visible message. Make the zone a focusable element with `role="button"`, `tabIndex=0`, Enter/Space handling, and a hidden file input opened on click.

## Testing Strategy

### Validation Approach

The strategy is two-phase: first write tests that surface each defect on the UNFIXED code, then verify the fix and prove preservation. Backend uses `pytest` with `pytest-asyncio` and `hypothesis`, with `httpx` calls mocked (no live network). Frontend uses `vitest` and React Testing Library. Reviews by the code-reviewer, security-reviewer and python-reviewer agents run after implementation as a gate.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate each defect BEFORE implementing the fix. Confirm or refute the root cause analysis. If refuted, re-hypothesize.

**Test Plan**: Write one failing test per defect class that encodes the expected behavior, and run on unfixed code.

**Test Cases**:
1. **Circular verification (C1)**: Claim with entities present in the document and no evidence expects UNVERIFIABLE (will fail on unfixed code).
2. **Unrelated Tavily result (C2)**: Result with score 0.82 and no shared tokens expects UNVERIFIABLE (will fail on unfixed code).
3. **LLM verdict (C3)**: Mocked Super returning `supports_claim=false` with no confirming quote expects not CONTRADICTED (will fail on unfixed code).
4. **Dates (C4)**: `12/31/2026` valid; `02/30/2026`, `2026-02-30`, "February 30, 2026", `02/29/2025` invalid (will fail on unfixed code).
5. **Empty claims (C5)**: Report score equals `compute_trust_score([])` (will fail on unfixed code).
6. **Malformed output (C6, C7)**: Confidence "high", entities `[1, null]`, category "Legal", list-shaped JSON, Tavily `score: null` (will fail on unfixed code).
7. **Upstream failure (C7)**: `httpx.TimeoutException` and missing key expect 502/503 with safe detail (will fail on unfixed code).
8. **Summary trust (C8)**: Mocked Ultra output with wrong counts or injected text expects replacement (will fail on unfixed code).
9. **Image (C9)**: PNG upload expects 501, not a placeholder (will fail on unfixed code).
10. **Concurrency (C10)**: Two concurrent requests with distinct mocked token counts keep separate usage (will fail on unfixed code).
11. **Upload and API (C11)**: Oversized stream gives 413 before full read; unknown challenge gives 404; Tavily request has Authorization header and no `api_key` in body (will fail on unfixed code).
12. **Frontend (C14)**: Failed challenge fetch shows an error; tab switch aborts; bad file rejected; Enter on dropzone opens picker (will fail on unfixed code).
13. **Config (C12, C13)**: Static checks that requirements are pinned and consistent, compose proxy target is not `localhost`, Dockerfile has a `USER` (may fail on unfixed code).

**Expected Counterexamples**:
- VERIFIED verdicts with empty external evidence, valid dates flagged, 500 on malformed JSON, global usage mixing between requests.
- Possible causes: circular substring rule, hard-coded support flag, missing boundary validation, module-level state.

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed pipeline produces the expected behavior.

**Pseudocode:**
```
FOR ALL X WHERE isBugCondition(X) DO
  result := verifyflow'(X)
  ASSERT no_crash(result)
     AND verdict_set_only_by_deterministic_verifier(result)
     AND no_unvetted_llm_text_in(result)
     AND valid_dates_not_flagged(result) AND invalid_dates_flagged(result)
     AND usage_isolated_per_request(result)
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed pipeline produces the same result as the original.

**Pseudocode:**
```
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT verifyflow(X) = verifyflow'(X)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many cases across the input domain automatically
- It catches edge cases that hand-written unit tests miss
- It gives strong guarantees that behavior is unchanged for non-buggy inputs

**Test Plan**: Capture current behavior on UNFIXED code for non-buggy inputs (golden outputs for `compute_trust_score`, `compute_risk_level`, bucket logic, response schema, routes), then assert the same after the fix.

**Test Cases**:
1. **Scoring preservation**: For random non-empty lists of statuses, `compute_trust_score` and `compute_risk_level` match the original formula and thresholds.
2. **Bucket logic preservation**: For random evidence lists with explicit `supports_claim` and scores, the original ordering (contradiction first, then support, then UNVERIFIABLE with counts) is unchanged.
3. **Schema and routes preservation**: `/health`, `/`, `/api/challenges`, known challenge ids and `VerificationReport` field names are unchanged; `TIER_ROUTING` keys and `api/index.py` import path unchanged.
4. **Valid upload preservation**: A valid PDF and a UTF-8 and latin-1 text file under the limit still produce a schema-valid report.
5. **Frontend rendering preservation**: A valid report renders scorecard, summary, claim cards, evidence chain and telemetry as before (snapshot).
6. **Verifier purity**: An import-graph test asserts `evidence_verifier.py` imports no `httpx`, `model_router` or network module.

### Unit Tests

- `validate_date` across US, European, ISO and written forms, leap years and 30-day months
- `agreement` for supports, conflicts and neutral cases, including number formatting (`$1,000` vs `1000`)
- `detect_injection` phrases and `sanitize_filename`
- `extract_claims` normalization of malformed items; `should_escalate` with mixed-case categories
- `verify_claim` rule order and reasons
- Tavily parser with null or missing fields; auth header present, key absent from body and logs
- Synthesizer validation: mismatched counts rejected, honest fallback wording
- Upload: oversized stream, bad signature, unsupported type ordering, image 501
- Challenge route 404

### Property-Based Tests

- Random calendar dates round-trip through formatting in each style and are accepted; random impossible day/month combinations are rejected
- Random claim and evidence text: `verify_claim` never returns VERIFIED without at least one agreeing external evidence item
- Random malformed JSON payloads (hypothesis recursive JSON strategies) never raise from `extract_claims` or the deep analyzer validator
- Random status lists: score in [0, 100], matches original formula for non-empty lists
- Random concurrent request interleavings keep per-request usage totals equal to each request's mocked tokens

### Integration Tests

- Full pipeline via FastAPI `TestClient` with mocked Nebius and Tavily: a mixed document yields correct counts, consistent score/risk, findings block first in summary
- Time-budget test: slow mocked Tavily with many claims returns a partial report with "Not checked within time budget" reasons within the limit
- Failure-mode test: Nebius down returns 502/503 with a safe message; Tavily down gives UNVERIFIABLE claims, not an error
- Docker config check: compose file and Vite config resolve the backend by service name
- Frontend flow: upload, tab switch with abort, challenge error banner, keyboard-operated dropzone
