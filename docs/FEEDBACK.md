# Platform Feedback — VerifyFlow

Everything below was observed while building and testing VerifyFlow. Numbers come from
`backend/eval_challenges.py` runs against the live API (4 adversarial documents plus 1 control,
short plain-text inputs).

## Models used

| Tier | Model ID | Used for |
|------|----------|----------|
| Nano | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | Claim extraction |
| Super | `nvidia/nemotron-3-super-120b-a12b` | Judging search snippets, finding conflicting statements |
| Ultra | `nvidia/Nemotron-3-Ultra-550b-a55b` | Final summary |

Tavily Search provides the web evidence. All model output is treated as a proposal; a rule-based
verifier (`evidence_verifier.py`) makes every verdict.

## Nebius Token Factory

**What worked**
- The OpenAI-compatible `/chat/completions` endpoint worked with plain HTTP calls. No special client was needed.
- `GET /v1/models` is a useful sanity check. It returned 30 models, five of them NVIDIA. VerifyFlow now calls it at startup and reports each configured tier as available or not at `/health`.
- Responses include `usage.total_tokens`, so per-tier token counts in the report are exact.

**Friction**
- **Model ID casing is inconsistent between models.** The Super ID is all lowercase
  (`nvidia/nemotron-3-super-120b-a12b`), while Nano and Ultra use mixed case. I first guessed
  `nvidia/Nemotron-3-Super-120b-a12b` and got a 404. Because I had written the pipeline to degrade gracefully, the
  failure was hidden and the Super tier did nothing until I listed the models. Copy IDs from `/v1/models`.
- **Intermittent unparseable JSON from the Super tier.** In one run, one Super call (evidence judging) returned a
  reply that failed JSON parsing, even with `response_format: json_object`. I did not capture the raw reply, so I
  can't say whether it was empty, truncated or wrapped in text. I added a retry with a larger `max_tokens` and
  logging of the reply head. The next full run had no failures, but that is one run, not proof of a fix.
- I could not use the `openai` Python SDK on my Windows machine because its `jiter` DLL was blocked by Windows
  Application Control. This is specific to my machine, not Nebius. Plain `httpx` against the REST endpoint worked
  without trouble.

**Measured usage (per document, tokens)**

| Tier | Range across 5 test docs |
|------|--------------------------|
| Nano | 693 – 2,072 |
| Super | 3,548 – 8,486 |
| Ultra | 502 – 1,114 |

Super uses the most tokens by far, because it judges all search snippets for a document in one batched call.
End-to-end time was 15–37 seconds per document, with web searches run 4 at a time.

## Tavily Search

- Each claim triggers one `search_depth: "advanced"` query. The response gives a URL, title, content snippet and
  score, which was enough to build a quote-level evidence check.
- A failed or empty search looks the same as "no evidence found" unless you check for it. VerifyFlow adds a
  visible note to the report when every search returns nothing.

## Would I adopt this in production?

_Not answered here. This section needs your own judgment after you've used the platform._
