# VerifyFlow

**Document verification where the evidence decides, not the model.**

> The model can think, but it does not get the final say. The evidence does.

VerifyFlow reads a document, extracts its factual claims, searches the live web for each one, and produces an
auditable trust report. NVIDIA Nemotron models *propose* judgments. A rule-based verifier written in plain code
(`backend/services/evidence_verifier.py`, no model calls) decides every verdict, and a model's judgment only counts
if it can quote its source.

Built for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/), Best Apps & Agents track.

- **Live demo:** https://verifyflow-blond.vercel.app (open Challenge Mode and run any document; a run takes 15 to 45 seconds)
- **Demo video:** _TODO: add the YouTube link before submitting_

## Who it is for

The first user is the person who approves payments or signs off on paperwork in a small business: an accounts
payable clerk, an office manager, a freelancer checking a contract. They receive invoices and agreements from
people they can't easily check, and the costly mistakes are specific: a "new bank details" invoice on a look-alike
domain, a contract with two different terms, a certificate from an agency that doesn't exist. VerifyFlow gives them
a per-claim report they can act on in a minute, with the quote or source behind each verdict, instead of an
AI opinion they have to take on trust.

## What it catches

Challenge Mode ships five adversarial documents. `backend/eval_challenges.py` runs them (plus a clean control
document) against a live backend and asserts the outcome:

| Challenge | What is wrong | How it is caught |
|-----------|---------------|------------------|
| Homograph bank URL | Domain uses a Cyrillic `а` instead of a Latin `a` | Deterministic check on the raw text, before any model sees it |
| Prompt injection | Hidden text tells the AI reviewer to mark everything verified; also dates a contract "February 30" | Pattern check for instructions aimed at a reviewer; calendar check for impossible dates |
| Fabricated authority | Cites an agency and a law that no source mentions | Search finds nothing independent; flagged as an unrecognized authority, never "verified" |
| Self-contradicting contract | 12-month and 24-month term; terminable and not terminable | A model reads the document and proposes conflicting quote pairs; code accepts a pair only if both quotes appear verbatim, then maps each quote to a claim by word overlap |
| Invoice with changed bank details | "Our banking details have changed" plus a payment link on a look-alike domain (Cyrillic `і`) | Same deterministic homograph check on the raw text; the report is rated high risk |

Latest runs: all 15 checks pass across the 6 documents. The control document (true statements about the Eiffel Tower) is never flagged or contradicted: no findings, trust between 56 and 100 depending on how many claims web search confirms, so risk is low or medium (medium when a true claim can't be confirmed by search).
Results depend on live web search and model output, so individual runs can vary.

### Compared with a plain LLM review

Every challenge also has a "plain LLM" button (`/api/baseline`): one Ultra call that reads the document and gives
an opinion, with no search and no verifier. To be clear about the result: in our runs the plain review also called
all five challenges suspicious and the control trustworthy. Nemotron Ultra is a capable reader. The difference is
what you can check afterwards. The plain review is a paragraph you have to trust. VerifyFlow gives one verdict per
claim, the exact quote or source URL behind it, the deterministic rule that fired, and a summary whose counts are
checked against the verifier before it is shown.

## How a verdict is made

```
Upload (PDF, TXT, MD)
  |
  v
Deterministic checks on raw text   -> look-alike domains, impossible dates, injected instructions
  |
  v
Nemotron Nano    extracts claims
  |
  v
Tavily           searches the web for each claim (4 in parallel)
  |
  v
Nemotron Super   PROPOSES a stance + verbatim quote for each snippet,
                 and proposes conflicts between statements in the document
  |
  v
Code verifier    accepts a proposal only if
                   - the quote really appears in the snippet / document
                   - the quote mentions the claim's named entity
                 and never lets the document vouch for itself
  |
  v
Nemotron Ultra   writes the summary (it cannot change a verdict)
```

Rejected proposals are shown in the UI as "REJECTED" so you can see what the model claimed and why it was ignored.
If a model call fails, the report says so in "analysis notes" and does not quietly return a weaker result.

**Scoring** (fixed constants, no model involved): the base score is `100 × (verified + 0.35 × unverifiable) / claims`, minus
30 per contradicted claim, 25 per high-severity finding and 10 per medium one. A document with any contradicted claim
or high-severity finding is at least "high" risk.

## Model usage

| Tier | Model | Role |
|------|-------|------|
| Nano | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | Claim extraction |
| Super | `nvidia/nemotron-3-super-120b-a12b` | Judge snippets, propose conflicts |
| Ultra | `nvidia/Nemotron-3-Ultra-550b-a55b` | Summary |

Served through Nebius Token Factory. Measured on the six test documents, Super uses the most tokens per document
(roughly 1.2k to 6.3k, against 0.7k to 3.1k for Nano and 0.6k to 1.2k for Ultra), because it judges every search
snippet and reads the whole document once for conflicts. Per-request calls: one Nano, two Super, one Ultra. Per-tier
token counts are shown in each report. See [docs/FEEDBACK.md](docs/FEEDBACK.md) for platform notes.

## Run it

You need Python 3 (developed on 3.14), Node 20+, a [Nebius Token Factory](https://studio.nebius.com/) key and a [Tavily](https://tavily.com/) key.

```bash
cp .env.example .env        # then add NEBIUS_API_KEY and TAVILY_API_KEY

# backend (http://localhost:8000, docs at /docs)
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --port 8000

# frontend (http://localhost:3000), in a second terminal
cd frontend
npm install
npm run dev
```

`GET /health` reports whether each configured model ID exists on the provider. Run the regression suite with the backend up:

```bash
cd backend
python eval_challenges.py
```

## Deploy (one container)

The root `Dockerfile` builds the React app and serves it from FastAPI, so the UI and API share one URL and port.
`render.yaml` is a [Render](https://render.com) blueprint for it: create a Blueprint from this repo, then set
`NEBIUS_API_KEY` and `TAVILY_API_KEY` in the dashboard. Keys are never stored in the repo, and `.dockerignore` keeps `.env` out of the image.

A public demo spends your API credits, so `/api/verify` is limited per client IP (`RATE_LIMIT_PER_HOUR`, default 30, `0` disables).
The limit is in-memory and trusts `X-Forwarded-For`, so it is a guard against accidents, not a security boundary.

**What is tested:** the single-origin setup (built frontend served by FastAPI at `/`, API under `/api`, `/health`, `/docs`) was run
locally and the regression suite passed against it. `docker compose up --build` was also run on Windows (Docker Desktop):
the image built, the container reported healthy, `/health` showed all three model tiers available, `/` served the UI, and a
real `POST /api/verify` returned a cited report in about 19 seconds. **What is not tested:** the Render deploy.

## Limits

- Text only: PDF (text layer), TXT, MD. Scanned PDFs and images are not supported.
- Verification is only as good as web search. A true but obscure claim is reported as unverifiable, not verified.
- The "unrecognized authority" and prompt-injection checks are pattern-based and will miss phrasings they don't list.
- A single run takes roughly 15 to 60 seconds.
- Upload size: the default cap is 4 MB (MAX_UPLOAD_SIZE_MB) because Vercel serverless functions reject request bodies above about 4.5 MB. Raise it only when self-hosting with Docker.
- Only the first 20 claims of a document are checked.

## Stack

FastAPI, React, Vite, Tailwind, httpx, Tavily Search API, NVIDIA Nemotron on Nebius Token Factory.

## License

[MIT](LICENSE)
