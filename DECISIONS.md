# Cabiran Shell Drying Planner — Judgment Calls

Single-file HTML app. No backend, no build step. All state in `localStorage` under key `cabiran.shellroom.v1`.

## Physical process constraints (hard limits from the plant)

- **Prime dry time — maximum 6 hours** between consecutive Prime dips. The chemistry allows longer, but exceeding 6h means the coat has dried too much and the next dip won't bond correctly. This is a hard upper bound, not a target.
- **Backup dry time — minimum 8 hours** between consecutive Backup dips. The coat must cure for at least 8h before re-dipping; going under this risks delamination. This is a hard lower bound.
- **Sandblasting — 1 hour, manual, between Prime dip 1 and Prime dip 2.** After the robot completes the Prime dip 1 sweep (~261 min for a full batch), an operator manually sandblasts all shells before dip 2 can start. Duration ≈ 60 min. This is operator-only; the robot is free but the 99-minute window remaining before the dip-2 deadline is too short to run a Backup dip (261 min), making the Prime phase effectively uninterruptible.
- **Batch size — maximum 38 hangers** (Prime conveyor physical capacity: 19 pairs × 2 columns).
- **Single robot** — one robot on a 7th-axis rail serves both Prime and Backup. All dip operations are serial through this shared resource.

These values are invariants — they come from chemistry and equipment, not from scheduling policy. Any simulation or planning tool must respect them.

## Pipeline flow and the real throughput constraint

The system is a pipeline: Prime → Backup → Hang-dry → Unhang → Floor-dry → DeWax.

When Prime is empty (no new batch loaded), it is **not** because of a scheduling failure. It is because Backup is full and cannot yet accept the Prime batch. Backup only frees space when the batch ahead of it has completed all its dips, dried, and been **unhanged** by an operator. Only then can Prime hangers transfer to Backup, and only then can new hangers be loaded onto Prime.

This means the **Unhang operation is the true gating constraint** on pipeline throughput:
- Unhang speed (operator) determines when Backup space opens
- Backup space opening determines when Prime can offload
- Prime offloading determines when the next batch can start

The robot is not idle during this wait — it is working Backup dips for the batch already there. The apparent "gap" between batches on Prime is the pipeline draining downstream, not a scheduling inefficiency.

**Relief actions in priority order:**
1. Faster unhanging (more operators, dedicated unhang crew) — directly shortens the wait
2. Expand Backup capacity (more hooks) — allows more batches in-flight simultaneously, reducing back-pressure on Prime
3. Second robot — speeds up Backup dip cycles so space opens sooner

## Defaults chosen

- **Cycle times (min per pair of shells):** dip1=15, dip2=15, dip3–7=12, seal=18. Brief did not specify; these are plausible values that produce a visually readable 7-day schedule. User can change freely.
- **Sandblasting:** start 08:00, duration 45 min. Aligns to each day's 06:00 anchor so dip 1 can complete on time.
- **Robot uptime:** 92% default. Editable via slider 50–100%.
- **Robot sequence:** `P, P, B, B, B, B, B, B` — robot serves prime twice (dip 1 then dip 2), then backup for dips 3–7 and seal. Matches the physical flow described in the brief.
- **Current-state snapshot:** prime=38 (full), backup=18. User can adjust.
- **Session anchor:** most recent Sunday 06:00 local time on first load. Persists across reloads.

## Simulation model

- A batch = 38 shells (all prime hangers). New batch starts each day at 06:00 as long as downstream capacity allows.
- Stage duration on the conveyor = `(cycleTimePerPair × 19) / uptime`. 19 pairs = full prime sweep.
- Sandblasting happens off-conveyor between dip 1 and dip 2.
- After seal dip: 12 h hang-dry (on hangers) + 12 h floor-dry (off) → shell becomes DeWax-ready.
- `DeWax-ready` is drawn as a 1-hour marker in the Gantt/viz to be visible. The actual ready state persists until consumed by the DeWax station.

## Visual decisions

- **Robot glyph:** single stylized SVG (column arm + base + rail + two indicator shells in batch colors). No 3D. Gently bobs and rotates with the scrubber to signal "live."
- **Hanger layout:** 19 rows × 2 cols for prime, 19 rows × 4 cols for backup. Hanger numbers 1–38 / 1–76 shown centered.
- **Batch coloring follows batches, not stages** — per brief. Seven muted pastels cycle by load day.
- **Active/queue zones:** soft dashed rectangles overlay the current pair and the next pair on prime, walking down the column as the scrubber advances.
- **Background** cream `#FAF7F2`, primary navy `#1F497D`. Inter for UI, Playfair Display for headings.

## XSS-safe DOM construction

The app never assigns HTML strings built from user input to DOM elements. Instead:

- `el(tag, attrs, children)` for all dynamic DOM construction — attributes escape automatically and children are wrapped in text nodes unless already DOM nodes.
- `textContent` for any free-text values (downtime reason, category labels).
- A small `setHTML(node, markup)` helper (via `<template>` parse) is used only for static markup strings that contain no user input — currently the DeWax chart's SVG string (numbers and fixed labels only).

## Optimizer

- Tries ±1 and ±2 minutes on each of the 8 cycle stages.
- Also tries one alternate robot sequence (`P-B` interleaved) as an additional candidate.
- Scores candidates by total 7-day shell output vs. baseline.
- Returns top 3 by Δ — if none beat the current plan, shows "plan looks well-tuned."

## Persistence

- Every state mutation (`save()`) writes the whole state object to `localStorage`.
- Reload restores the full session including scrubber position, page, logs, and locked plan.
- `Reset` button wipes back to `DEFAULT_STATE()` after a confirm prompt.

## What's explicitly out of scope

- No backend, no accounts, no network writes.
- No mobile breakpoints beyond what Tailwind's default grid gives for free at ≥1024 px.
- No i18n. UI is English, per brief.

---

## Post-peer-review refactor (April 2026)

After two independent peer reviews flagged **model fidelity** as the dominant limitation,
the following ten-phase refactor was planned and executed in order:

### Phase 2 — Event-driven dispatcher rewrite
Replaced the sort-once-then-walk serializer with an event-driven dispatcher that picks, at
each step, the ready instance whose `earliestStart` is lowest. Tie-breakers: user's `tp`
rank, then `batchPriority`, then stage index. This fixes the Batch #2 "lost-its-turn" bug
where a 10 min `dryAfter` caused a 239 h scheduling gap.

### Phase 3 — Schema versioning
Introduced `SCHEMA_VERSION`, a `MIGRATIONS` map, and `migrateIfNeeded()` called from
`load()`. Every `save()` writes `_schemaVersion`. Older saved states back-fill missing
fields without data loss. v1 → v2 migration adds: `confirmed`, `batchSizes`, `rules`,
`logs.spills`.

### Phase 4 — Explicit resource model
`state.config.resources = { operators, sandStations }`. The dispatcher now maintains a
pool of `freeAt` timestamps per resource kind: robot (always 1), operators (default 2),
sand station (default 1). Operator tasks pick the earliest-free operator slot, so Hang of
Batch #2 can run in parallel with Unhang of Batch #1 if both have free operators.

### Phase 5 — Planner as the landing tab
Tab order: Planner → Live Conveyor → Forecast → Gantt → Robot Log → MES Log → Plan Lock →
Rules. Default landing page = 7 (Planner). No features are hidden for any persona.

### Phase 6 — MES is documentation-only
Added a banner at the top of the MES Log tab stating that Forecast is config-driven and
does *not* learn from actuals. A feedback loop between MES actuals and Forecast is parked
for v2 (reviewer #1 argued for it; user decided not now).

### Phase 7 — Auto-spill audit trail
Every Size reduction that sheds shells now appends to `state.logs.spills` with
`{ts, batchIdx, oldSize, newSize, shed:[{field, amount}]}`. MES Log shows an
"Auto-adjustments" table so "where did those 8 shells go?" has a visible answer.

### Phase 8 — UX / accessibility polish
- Every batch chip gets a 1px navy border at `rgba(10,31,61,0.4)`, raising WCAG-AA
  contrast of pastel colours.
- "FREE" renamed to "idle" in the Planner day rows, with a tooltip clarifying the
  robot-idle time is blocked by operator work or dry gates — not bookable for more
  production unless upstream constraints shorten.
- "X of 38 loaded" / "Y of 76 loaded" annotations above the Prime / Backup columns on the
  Live Conveyor when a batch is partially loaded.
- `aria-label` on every robot and operator chip, with `role="button"` and `tabindex=0`.

### Phase 9 — Documentation
- JSDoc `@typedef` block near the top of the `<script>` documents the shape of `state`,
  `config`, `forecast`, every record type. No TypeScript migration; pure docs.
- `DECISIONS.md` (this file) appended with the above.
- `PEER_REVIEW.md` gets a Review Response Log appendix mapping each reviewer point to the
  phase that handled it.

### Phase 10 — Verification
- `test.html` runs 9 scenarios; scenarios S8 and S9 were pinned as expected-to-fail before
  Phase 2 and are expected to flip to passing after. User runs this manually by opening
  `test.html` in Chrome once the dev server is up.

### Explicitly out of scope for this refactor pass

- **TypeScript / multi-file split** — deferred; the single-file constraint stands.
- **MES-to-forecast feedback loop** — parked for v2 per user decision.
- **Genetic-algorithm optimizer** — the heuristic optimizer is acceptable with the
  objective function now explicit in the dispatcher.
- **Mobile / responsive beyond desktop** — retained original out-of-scope.
- **DST correctness** — `test.html` scenario S4 is a smoke test; deeper epoch-UTC
  refactor is parked.
