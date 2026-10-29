---
inclusion: auto
name: Design Quality
description: Frontend design quality standards, anti-slop rules, and design review heuristics. Ported from pbakaus/impeccable. Triggers when working on UI files or frontend design.
---

# Design Quality Standards

> Ported from [pbakaus/impeccable](https://github.com/pbakaus/impeccable) — design vocabulary for coding agents. Licensed Apache 2.0.

## Core Principle

Every UI change ships with craft. No hedging, no shortcuts. Work as an award-winning design director would: production-grade code, a clear point of view, and exceptional attention to detail.

## Surface Modes

Choose the mode based on what the visitor's success looks like:

| Mode | Purpose | Design Priority |
|------|---------|----------------|
| **Persuade** | Visitor decides and acts (landing pages, pricing, campaigns) | Earn attention and action. Bold, distinct work. |
| **Operate** | Visitor completes a task (app UI, dashboards, settings) | Scanability, consistency, native expectations. Brand in precise details. |
| **Read** | Visitor understands something (docs, articles, guides) | Structure for comprehension. Make reading worth staying for. |
| **Experience** | Visitor is inside the work (portfolios, galleries) | Let the artifact lead. Interface recedes. |

## Anti-Slop Rules (Deterministic)

These patterns indicate AI-generated "default" design. Avoid them:

### Typography
- Don't default to Inter for everything
- Don't use the same font for headings and body without intentional pairing
- Don't skip heading levels (h1 → h3)
- Don't use thin/light font weights below 16px
- Don't set body text smaller than 16px on desktop

### Color & Visual
- Don't default to purple-to-blue gradients
- Don't use gray text on colored backgrounds (contrast fail)
- Don't default to rounded-square icon tiles above every heading
- Don't nest cards inside cards without clear visual hierarchy
- Don't add decorative borders/shadows to every container

### Layout & Spacing
- Don't use cramped padding (< 16px in interactive elements)
- Don't center-align long paragraphs of text
- Don't use equal spacing everywhere — create visual rhythm
- Don't make every section full-width with no max-width constraint

### Interaction
- Don't default to pill-shaped buttons on everything
- Don't add hover effects that provide no feedback
- Don't hide primary actions behind hamburger menus on desktop
- Don't use loading spinners where skeleton screens would work

## Design Review Heuristics

When reviewing or creating UI, check these in order:

### 1. Hierarchy (Is the important stuff obvious?)
- Clear visual weight differences between primary, secondary, tertiary elements
- One dominant element per viewport
- Intentional use of whitespace to separate groups

### 2. Consistency (Does it feel unified?)
- Consistent spacing scale (4px, 8px, 16px, 24px, 32px, 48px, 64px)
- Color palette limited to 3-5 core colors + neutrals
- Typography scale with clear purpose for each size
- Component reuse over one-off styling

### 3. Usability (Can people actually use it?)
- Touch targets minimum 44x44px on mobile
- Labels on form inputs (not just placeholders)
- Clear affordances (buttons look clickable, links look linked)
- Error states, empty states, loading states all designed
- Keyboard navigation works

### 4. Accessibility (Does it work for everyone?)
- Color contrast meets WCAG AA (4.5:1 for text, 3:1 for large text)
- Focus indicators visible
- Alt text on images
- Semantic HTML structure
- Screen reader-friendly content order

### 5. Responsiveness (Does it work on all screens?)
- Mobile-first layout consideration
- No horizontal scroll on mobile
- Touch-friendly on tablets
- Readable without zoom on any device

## Design Commands (Mental Model)

When working on UI, think in terms of these operations:

- **critique [target]** — Score the design against usability heuristics, rank what to fix first
- **audit [target]** — Check accessibility, performance, theming, responsive behavior
- **polish [target]** — Final pass before shipping
- **bolder [target]** — Amplify safe/bland designs
- **quieter [target]** — Tone down aggressive/overstimulating designs
- **distill [target]** — Remove what the page doesn't need
- **harden [target]** — Production-ready: errors, i18n, overflow, edge cases

## Refinement vs Redesign

- **Refinement** preserves identity, behavior, copy, and everything outside scope
- **Redesign** keeps product truth and function but treats the old look as anti-reference
- Never split the difference into polish on the discarded look
- Ask before replacing factual copy or adding claims
