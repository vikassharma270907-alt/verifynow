# VerifyFlow: Agent Handoff (as of 2026-10-30)

Give this file to the next agent as its first message, or tell it to read `docs/HANDOFF.md`.

## 0. How to use this file
1. Open the project folder (`d:\kiro`, or a fresh clone of the GitHub repo) in the new agent.
2. Send: "Read docs/HANDOFF.md, .kiro/steering/project-context.md, .kiro/steering/lessons-learned.md and .kiro/memory/session-log.md. Then work through section 7."
3. Kiro agents load `.kiro/` automatically. Claude Code and other agents read `.claude/` only, so tell them to treat `.kiro/steering/*.md` and `.kiro/skills/` as plain instruction files.
4. Run only one agent at a time on the repo.

### What is NOT in git (a fresh clone will not have it)
- `.env` (local API keys). Copy it over separately. Never paste keys into chat.
- Vercel environment variables (already set in production).
- `everything-claude-code/` (full ECC clone, git-ignored). Share it as a zip, or install into another project with:
  `powershell -ExecutionPolicy Bypass -File "d:\kiro\everything-claude-code\.kiro\install-to-project.ps1" <target>` (add `-Force` to overwrite existing files).
- `backend/.hypothesis/`, `__pycache__/` and `graphify-out/` caches.

### What IS in git
- `.kiro/` (16 agents, 19 skills, 24 steering files, 16 hooks, 2 scripts, memory log, specs) and `.claude/skills/frontend-design`.
- Design rules: `.kiro/steering/design-quality.md` (impeccable + frontend-design) and `skills-lock.json`.
- Not ported: the impeccable and Claude-Mem runtimes. Only their rules were kept. Memory is a markdown log.

## 1. What this is
VerifyFlow is an AI document-verification agent for the Nebius x NVIDIA Global AI Hackathon (Best Apps & Agents track). Deadline: Oct 30, 2026, 10:00 AM PDT (= 10:30 PM IST, Oct 30).

Core principle: "The model can think, but it does not get the final say. The evidence does." Every LLM output is an untrusted claim. A deterministic code verifier makes the final trust call.

## 2. Location and state
- Workspace: `d:\kiro` (Windows, PowerShell, Python 3.14). Branch `master`, HEAD `f1d02a0` when this was written.
- An auto-sync job commits and pushes to origin/master every few minutes. Pushing to master triggers a Vercel production deploy (~1 min).
- Live demo: https://verifyflow-blond.vercel.app. Check `/health` for `nebius_configured` and `tavily_configured`. Both keys were added to Vercel production on Oct 30.
- Last recorded: 166 backend tests and 9 frontend tests passing. Live eval `backend/eval_challenges.py` scored 15/15 on two runs. Re-run before trusting this.

## 3. Architecture
- Backend: FastAPI in `backend/`. Frontend: React + Tailwind + Vite in `frontend/`. Vercel entry is `api/index.py`, which inserts `backend/` into `sys.path`.
- Models via the Nebius Token Factory (OpenAI-compatible), called with raw `httpx` and not the openai SDK. The SDK's `jiter` DLL is blocked by Windows Application Control.
  - Nano: claim extraction and classification.
  - Super: evidence judging and conflict detection. The ID is all lowercase: `nvidia/nemotron-3-super-120b-a12b`.
  - Ultra: summary only, 7 s cap.
- Tavily Search: live web grounding. The `api_key` goes in the JSON body, not a header.
- Key files:
  - `backend/services/evidence_verifier.py`: deterministic trust gate. It must never contain LLM calls.
  - `backend/services/model_router.py`, `claim_extractor.py`, `deep_analyzer.py`, `tavily_grounder.py`, `synthesizer.py`, `claim_checks.py`, `document_checks.py`
  - `backend/routers/verify.py` (main pipeline), `challenge.py` (adversarial docs), `baseline.py` (plain-LLM comparison), `health.py`
  - `backend/config.py`: model IDs, `TIER_ROUTING`
  - `backend/eval_challenges.py`: live regression script
  - `backend/tests/`: pytest suite
  - Spec: `.kiro/specs/verifyflow-full-bug-audit-fix/`
- Deployment: `vercel.json` (`maxDuration` 60, frontend built into `frontend/dist`). A one-container Dockerfile also exists. Docker is untested.

## 4. Verifier design rules (do not break)
1. Models only propose. A proposal counts only if it cites a quote that appears verbatim in the source AND the quote mentions the claim's proper-noun subject entity.
2. The document cannot be its own evidence. Claims found only in the document are reported as "stated in document, not independently verified".
3. Claims about the document itself ("this agreement", "Section 3") and number/date-only claims cannot be verified by web sources.
4. Run deterministic checks (homograph domains, impossible dates, injected instructions) on the RAW text before any model sees it.
5. Never fail silently. Failed or skipped model steps go into `analysis_notes` in the report.
6. Ask models for quotes, not IDs. Code maps quotes to claims.
7. Every await in a request is wrapped in `asyncio.wait_for` against one deadline of about 50 s (Vercel kills at 60 s).
8. Retry on transport errors and HTTP 429/502/503/504/529.

## 5. Project rules
- Never pass raw LLM output to users without verifying it.
- Keep `evidence_verifier.py` deterministic.
- Route to the cheapest capable tier.
- API keys come from environment variables only. `.env.example` has the template (`NEBIUS_API_KEY`, `TAVILY_API_KEY`).
- Known mismatch: the "85/10/5 Nano/Super/Ultra" rule is NOT met. Each request makes 1 Nano, 2 Super and 1 Ultra call, and Super uses the most tokens. The README documents the measured split.

## 6. Honest findings (keep submission docs consistent)
- A plain Ultra baseline (`/api/baseline`) also caught all 5 challenge docs. The honest differentiator is auditable, rule-backed findings, not detection rate.
- Run times are 15-58 s per document and vary between runs. Report ranges, not best runs.
- A slow invoice run finished in 52 s with "evidence review skipped". If that becomes common, reduce `MAX_CLAIMS` or the Super batch size.
- `docs/FEEDBACK.md` must contain only measured results.

## 7. Remaining TODO / risks
1. Submission checklist: hosted demo URL (done), public repo with visible LICENSE (verify), public YouTube video of 3 minutes or less (not confirmed), written feedback in `docs/FEEDBACK.md` (re-check for unmeasured claims), submit before the deadline.
2. API keys were pasted in chat earlier. Rotate them, update the Vercel env vars, redeploy.
3. Re-check production `/health` before submitting.
4. Disable the auto-push job before the final push if you want reviewed commits only.
5. Docker path is untested. Say "untested".
6. Optional: update the 85/10/5 rule in `.kiro/steering/project-context.md` to match reality.

## 8. Operating tips for this machine
- Check `git status` and `git log` before debugging odd behavior (auto-sync and other agents edit the repo).
- Local eval: start the backend on a fresh port with `RATE_LIMIT_PER_HOUR=0`.
- Keep foreground commands under about 60 s. Use background processes for long runs.
- PyPI is flaky. Use `uv` with `$env:UV_HTTP_TIMEOUT = "600"`. Use `>=` pins (Python 3.14).
- `graphify` is at `%APPDATA%\Python\Python314\Scripts\graphify.exe`. Knowledge graph is in `graphify-out/`.
- Kiro PreToolUse hooks often block the first write. Answer briefly and retry the identical call.
- Built-in reviewer agents have no file tools here. Use general-task-execution with review instructions.
- Before saying "ready", run `backend/eval_challenges.py` live, read the backend log, run `vercel env ls` and check `/health` after any deploy.
- Never write measured-sounding claims in README or FEEDBACK without a run that produced them.
