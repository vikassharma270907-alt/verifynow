---
inclusion: auto
name: Superpowers Methodology
description: Brainstorming-first development, systematic debugging, and subagent-driven development. Ported from obra/superpowers for Kiro.
---

# Superpowers Methodology

> Ported from [obra/superpowers](https://github.com/obra/superpowers) — a complete software development methodology for coding agents.

## Brainstorming-First Principle

Before writing any code for a new feature, product, or non-trivial change:

1. **Draw out intent.** Ask what the user is really trying to do, and why. Don't jump into implementation.
2. **Play back understanding.** Summarize what you heard in chunks short enough to actually read and digest.
3. **Get sign-off.** Small changes can be agreed in chat. Projects need a written design document a builder could plan from.
4. **Only then plan.** Break work into bite-sized tasks (2-5 minutes each) with exact file paths, code snippets, and verification steps.

### When to Brainstorm
- New features or products
- Architectural changes
- Anything where the user says "build me..." without a detailed spec
- Refactoring that touches >3 files

### When to Skip
- Bug fixes with clear reproduction steps
- Single-file changes
- Explicit "just do it" instructions

## Systematic Debugging (4-Phase Process)

When something is broken, follow this exact sequence:

### Phase 1: Reproduce
- Get the exact error message, stack trace, or failing behavior
- Create a minimal reproduction
- Confirm the bug exists in a clean state

### Phase 2: Isolate
- Binary search through recent changes if possible
- Add logging/breakpoints to narrow the scope
- Identify the exact line or function where behavior diverges

### Phase 3: Root Cause
- Trace backwards from the failure point
- Check assumptions: types, null checks, async timing, state mutations
- Look for defense-in-depth gaps

### Phase 4: Fix + Verify
- Write a test that reproduces the bug FIRST (red)
- Apply the minimal fix
- Verify the test passes (green)
- Check for similar patterns elsewhere (same bug in other places)

**Rule: If you've tried the same approach twice and it failed, stop. Diagnose the root cause before trying again.**

## Subagent-Driven Development

For larger features, delegate tasks to specialized sub-agents:

1. **Plan phase:** Break the approved design into ordered tasks
2. **Execute phase:** Dispatch each task to a sub-agent with clear context:
   - Exact files to modify
   - Expected behavior
   - Verification steps (tests to write/run)
3. **Review phase:** After each sub-agent completes, review against the plan
4. **Continue/fix:** If review passes, move to next task. If not, fix before continuing.

### Task Sizing
- Each task: 2-5 minutes of focused work
- Each task has a single clear deliverable
- Dependencies between tasks are explicit
- Every task ends with a verification step

## Verification Before Completion

Before declaring any work done:
1. Run the build — it must pass
2. Run relevant tests — they must pass
3. Manually verify the change does what was requested
4. Check for regressions in related functionality

**"It compiles" is not verification. "Tests pass" is closer. "It works as the user described" is the bar.**

## Philosophy

- **Test-Driven Development** — Write tests first, always
- **Systematic over ad-hoc** — Process over guessing
- **Complexity reduction** — Simplicity as the primary goal
- **Evidence over claims** — Verify before declaring success
- **YAGNI** — You Aren't Gonna Need It. Don't build abstractions ahead of demand.
