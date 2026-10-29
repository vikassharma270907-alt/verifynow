---
inclusion: auto
name: Design Quality
description: Frontend design quality standards, anti-slop rules, design process, and review heuristics. Merged from pbakaus/impeccable and anthropics/claude-plugins-official frontend-design skill. Triggers when working on UI files or frontend design.
---

# Design Quality Standards

> Merged from [pbakaus/impeccable](https://github.com/pbakaus/impeccable) (Apache 2.0) and [anthropics/claude-plugins-official/frontend-design](https://github.com/anthropics/claude-plugins-official) (see LICENSE.txt).

## Core Principle

Every UI change ships with craft. No hedging, no shortcuts. Work as the design lead at a studio known for giving every client a distinct visual identity not mistaken for anyone else's. Make deliberate, opinionated choices about palette, typography, and layout that are specific to the brief.

---

## 1. Ground Every Design in the Subject Matter

Before touching any code or visuals:

1. **Identify the product/subject** — what is this for?
2. **Identify the audience** — who will use it?
3. **Identify the primary job** — what must the visitor accomplish?

The subject's industry, materials, and vernacular are where distinctive visual choices come from. A toy for girls aged 8–11 looks nothing like a financial analyst dashboard. Build with the brief's real content throughout.

## 2. Surface Modes

Choose the mode based on what the visitor's success looks like:

| Mode | Purpose | Design Priority |
|------|---------|----------------|
| **Persuade** | Visitor decides and acts (landing pages, pricing, campaigns) | Earn attention and action. Bold, distinct work. |
| **Operate** | Visitor completes a task (app UI, dashboards, settings) | Scanability, consistency, native expectations. Brand in precise details. |
| **Read** | Visitor understands something (docs, articles, guides) | Structure for comprehension. Make reading worth staying for. |
| **Experience** | Visitor is inside the work (portfolios, galleries) | Let the artifact lead. Interface recedes. |

---

## 3. Design Process: Plan → Review → Build → Critique

### Pass 1: Design Plan

Create a compact token system before writing any code:

- **Color:** 4–6 named hex values for the core palette. Describe intent for each.
- **Type:** Typeface(s) and their roles. One family or two clearly distinct ones. Never default to Inter/system-ui for everything.
- **Layout:** One-sentence prose + ASCII wireframes. Include alignment guidance (left, center, justified).
- **Principles:** 2–3 high-level statements about what makes this page unique.

### Pass 2: Review Against the Brief

Before building, check each part of the plan. If any choice reads as the generic default you would produce for any similar page — revise it. Say what you changed and why.

### Pass 3: Build

Follow the revised plan. Be careful with CSS selector specificities — generated classes often cancel each other out (especially padding/margin between sections).

### Pass 4: Self-Critique

Critique your own work as you build. Apply the Chanel test: before shipping, remove one accessory. Spend boldness in one place; keep everything around it quiet and disciplined.

---

## 4. Anti-Slop Rules (Deterministic)

These patterns indicate AI-generated "default" design. Avoid them unless the brief specifically calls for them.

### 5 AI-Generated Design Tells

1. **Warm cream + terracotta** — near #F4F1EA background with high-contrast serif and #D97757 accent. Reads as "Claude-generated."
2. **Dark + acid accent** — near-black background with bright acid-green or vermilion single accent.
3. **Broadsheet layout** — hairline rules, zero border-radius, dense newspaper columns.
4. **SaaS card kit** — identical rounded cards, same border-radius on everything, soft grey shadow (rgba(0,0,0,.1)), gradient washes as decoration.
5. **Template chrome** — tracked-out ALL-CAPS eyebrows, middle-dot separators (A · B · C), spaced em dashes (WORD — fragment), tinted near-black (#0B0B0B), monospace data labels, → appended to links.

### Typography Anti-Slop
- Don't default to Inter/system-ui for everything
- Don't use the same font for headings and body without intentional pairing
- Don't skip heading levels (h1 → h3)
- Don't use thin/light font weights below 16px
- Don't set body text smaller than 16px on desktop
- Don't accent a single word in a headline with italic/bold/different color
- Don't use ALL CAPS for labels by default
- Don't add unnecessary typographic labels above content

### Color & Visual Anti-Slop
- Don't default to purple-to-blue gradients
- Don't use gray text on colored backgrounds (contrast fail)
- Don't default to rounded-square icon tiles above every heading
- Don't nest cards inside cards without clear visual hierarchy
- Don't add decorative borders/shadows to every container

### Layout & Spacing Anti-Slop
- Don't use cramped padding (< 16px in interactive elements)
- Don't center-align long paragraphs of text
- Don't use equal spacing everywhere — create visual rhythm
- Don't make every section full-width with no max-width constraint

### Interaction Anti-Slop
- Don't default to pill-shaped buttons on everything
- Don't add hover effects that provide no feedback
- Don't hide primary actions behind hamburger menus on desktop
- Don't use loading spinners where skeleton screens would work

---

## 5. Typography

Typography carries the personality of the page.

- Use one typeface family or two clearly distinct ones. Choose deliberately for the brief, not defaults.
- Set a clear type scale following The Elements of Typographic Style: intentional weights, widths, spacing.
- Default to line lengths < 80 characters.
- Serif body text gets slightly more line-height than sans-serif.
- When type is used as a headline or visual element, make the treatment an active design choice, not a neutral delivery vehicle.
- Numbered markers (01 / 02 / 03) are only appropriate if the content is actually a sequence.

---

## 6. Motion

- Use non-user-triggered motion sparingly. One orchestrated moment (page-load sequence or reveal) beats scattered effects.
- Fade-and-slide-up on every section = generic AI default. Avoid.
- Motion that answers a user action (opening, expanding, confirming) is welcome when it shows what changed.
- Respect `prefers-reduced-motion`.

---

## 7. UX Writing

Words appear in a design to make it easier to understand and use. They are design content, not decoration.

- **Write from the user's perspective.** "Manage notifications," not "Webhook config."
- **Active voice.** CTAs say exactly what happens: "Save changes," not "Submit."
- **Consistent vocabulary.** If the button says "Publish," the toast says "Published."
- **Failure = direction.** Errors explain what went wrong and how to fix it. No apologies, no vagueness.
- **Empty states = invitations.** An empty screen tells the user what to do next.
- **Sentence case, plain verbs, no filler.** Match tone to the brand and audience.

---

## 8. Design Review Heuristics

When reviewing or creating UI, check in this order:

### Hierarchy (Is the important stuff obvious?)
- Clear visual weight differences between primary, secondary, tertiary elements
- One dominant element per viewport
- Intentional use of whitespace to separate groups

### Consistency (Does it feel unified?)
- Consistent spacing scale (4px, 8px, 16px, 24px, 32px, 48px, 64px)
- Color palette limited to 3–5 core colors + neutrals
- Typography scale with clear purpose for each size
- Component reuse over one-off styling

### Usability (Can people actually use it?)
- Touch targets minimum 44x44px on mobile
- Labels on form inputs (not just placeholders)
- Clear affordances (buttons look clickable, links look linked)
- Error states, empty states, loading states all designed
- Keyboard navigation works

### Accessibility (Does it work for everyone?)
- Color contrast meets WCAG AA (4.5:1 for text, 3:1 for large text)
- Focus indicators visible
- Alt text on images
- Semantic HTML structure
- Screen reader-friendly content order

### Responsiveness (Does it work on all screens?)
- Mobile-first layout consideration
- No horizontal scroll on mobile
- Touch-friendly on tablets
- Readable without zoom on any device

---

## 9. Design Operations

Mental model for working on UI:

- **critique [target]** — Score against usability heuristics, rank what to fix first
- **audit [target]** — Check accessibility, performance, theming, responsive behavior
- **polish [target]** — Final pass before shipping
- **bolder [target]** — Amplify safe/bland designs
- **quieter [target]** — Tone down aggressive/overstimulating designs
- **distill [target]** — Remove what the page doesn't need
- **harden [target]** — Production-ready: errors, i18n, overflow, edge cases

## 10. Refinement vs Redesign

- **Refinement** preserves identity, behavior, copy, and everything outside scope
- **Redesign** keeps product truth and function but treats the old look as anti-reference
- Never split the difference into polish on the discarded look
- Ask before replacing factual copy or adding claims
