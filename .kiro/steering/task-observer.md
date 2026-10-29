---
inclusion: auto
name: Task Observer
description: Meta-observation skill that watches work sessions, captures patterns and corrections, and turns them into improvements. Ported from rebelytics/one-skill-to-rule-them-all.
---

# Task Observer

> Ported from [rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all) — the meta-skill that builds and improves skills. Licensed CC BY 4.0, created by Eoghan Henn.

## Purpose

Skills and steering files that never learn from how you actually use them stay frozen. Task Observer watches your work sessions and does two things:

1. **Identifies new patterns** — spots repeating approaches, corrections, and gaps that could become steering rules or lessons learned
2. **Improves existing guidance** — notices when steering rules don't match actual practice and suggests updates

## What to Observe

During every session, watch for:

### Corrections and Adjustments
- User adjusts agent output or steers in a different direction → signal that steering could be clearer
- User repeatedly asks for the same style/approach → candidate for a steering rule
- User explicitly says "remember this" or "always do X" → immediate lesson-learned entry

### Gaps No Rule Covers
- Manual work that could be systematized → candidate for a new hook or steering rule
- Repeated questions about the same topic → candidate for documentation
- Workarounds for tool limitations → candidate for lessons-learned

### Cross-Cutting Principles
- Patterns that apply across multiple files/features, not just one skill
- Quality standards that should be universal
- Error patterns that keep recurring

## Observation Format

When logging an observation, use this structure:

```
### [TYPE] Short Description
- **Session:** [date or context]
- **What happened:** [factual description]
- **Signal:** [what this tells us about the steering/patterns]
- **Suggested action:** [specific change to make]
- **Affected files:** [which steering/hook files to update]
```

## Where Observations Go

1. **Immediate:** High-confidence patterns go directly into `lessons-learned.md`
2. **Staged:** Lower-confidence observations go into `memory/session-log.md` for review
3. **Promoted:** After 2-3 occurrences of the same pattern, promote from session log to lessons-learned

## The Self-Improving Part

Task Observer also observes itself:
- If observations miss important patterns → adjust observation criteria
- If observation format is unclear → improve the format
- If observations create noise → narrow the trigger conditions

## Rules

1. **Never modify steering files without user review.** Observations are proposals. Nothing changes until the user approves.
2. **Same rule broken twice → structural fix.** If the same pattern gets flagged twice, the fix is a hook, lint rule, or default — not another rewording of the steering rule.
3. **Additive changes can be applied directly.** Adding a new example or clarification to an existing pattern is safe. Restructuring or new rules need review.
4. **Keep observations concise.** One paragraph per observation, with a clear action item.

## Integration with Existing Hooks

- `extract-patterns` hook (Stop trigger) handles end-of-session pattern extraction
- `session-summary` hook (Stop trigger) captures what was accomplished
- This steering file provides the methodology those hooks should follow
