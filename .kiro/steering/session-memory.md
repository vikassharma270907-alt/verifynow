---
inclusion: auto
name: Session Memory
description: Persistent context management across sessions. Captures observations, decisions, and patterns for future session injection. Ported from thedotmack/claude-mem.
---

# Session Memory

> Inspired by [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) — persistent context across sessions. Licensed Apache 2.0.

## Purpose

Context dies when a session ends. This steering file defines how to capture important observations during work and make them available to future sessions.

## Observation Types

When working, capture observations in these categories:

| Type | Description | Example |
|------|-------------|---------|
| **decision** | Architectural or design choice made | "Chose Zustand over Redux for state management" |
| **bugfix** | Bug found and its root cause | "Race condition in auth — token refresh overlapping with API calls" |
| **pattern** | Reusable approach discovered | "Table-driven tests work well for validator functions" |
| **correction** | User corrected agent behavior | "User prefers explicit error types over generic Error" |
| **security_alert** | Security issue found | "API key was being logged in debug mode" |
| **performance** | Performance insight | "N+1 query in user list endpoint — batch with IN clause" |

## Where Observations Live

Observations are stored in two places:

1. **`.kiro/steering/lessons-learned.md`** — Durable, cross-session patterns. Edit this directly.
2. **`.kiro/memory/session-log.md`** — Recent session observations. Auto-appended by hooks.

## Session Start Context

At session start, check these files for prior context:
1. Read `lessons-learned.md` for established patterns
2. Scan `memory/session-log.md` for recent observations relevant to current work
3. Apply relevant context without re-explaining to the user

## Progressive Disclosure

Don't dump all history at once. Layer context:
1. **Always inject:** Active project patterns from `lessons-learned.md` (loaded via steering)
2. **On demand:** Search `session-log.md` when encountering a problem that might have been solved before
3. **Deep dive:** Read full observation details only when the summary isn't enough

## Privacy

- Never store API keys, passwords, or secrets in observation logs
- Use `<private>` tags to exclude sensitive content from storage
- Reference secrets by key name, not value

## Maintenance

- Review `session-log.md` periodically — promote valuable patterns to `lessons-learned.md`
- Archive old entries (>30 days) that haven't been promoted
- Keep `lessons-learned.md` focused and actionable
