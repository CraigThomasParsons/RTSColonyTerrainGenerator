# Daedalus — the autonomous worker loop

Status: **design draft** (2026-07-20), not yet built. This is the design record +
build sequencing for **Daedalus**, an autonomous per-ticket coding loop that runs
a chain of planned work (sprints / epics / a queue of issues) with little or no
human babysitting, so the maintainer can offload coding — especially when the
interactive Claude session is rate-limited.

Daedalus is the **worker loop**. It is the inner, per-ticket half of the
**NightCrew** coordinator design (AMPB `docs/plans/the-night-crew.md`), which
specs the central job board but deliberately leaves the runtime loop undetailed.
It pairs with — and mostly **ports + extends** — the AMPB "Night Shift"
reviewer/remediator tooling. Where that tooling already exists it is cited rather
than reinvented.

Naming: **Daedalus** = the runnable loop + the duplicated Hermes instance that
hosts/notifies it (the day-coding sibling of the maintainer's work agent
**Nyx**). See [`00-nyx-recon.md`](00-nyx-recon.md) for the host-layer status.

---

## Problem

The maintainer wants a Hermes-driven agent that loops through a well-planned
chain of work (sprints, epics, or any queue of tickets) and, for each ticket:
implements it test-first, tightens it, hardens its architecture, gets it reviewed
by a **different model** than the one that wrote it, applies that feedback over a
few rounds, then opens a PR and pings a human on Discord. The pieces exist but are
scattered across two repos and two forges, and the review loop has no explicit
simplify/architecture passes and no convergence rule.

## What already exists (do not rebuild)

All in AMPB unless noted; all are the reference implementations Daedalus reuses:

- **Ticket launch:** `scripts/tools/start_gitea_issue.py <N> --launch` — cleans
  the tree, cuts `feature/<slug>` from the base branch, launches a headless agent
  via `scripts/tools/prompt_generator.py` + `scripts/tools/agents/*_adapter.py`.
- **Multi-model adapters:** `scripts/tools/agents/` — `claude_adapter.py`,
  `grok_adapter.py` (xAI Grok Build CLI, headless `grok -p` / `grok agent`,
  SuperGrok-authed), `codex_adapter.py`, `ollama_adapter.py`. These make the
  *implementer* model swappable, which is the rate-limit escape hatch.
- **Cross-model reviewer:** `scripts/tools/ai_pr_reviewer.js` +
  `.gitea/workflows/pr_ai_reviewer.yml` — a trusted Gitea Actions job that pulls
  the PR diff from the Gitea API, asks a **provider chain (Gemini → mammouth.ai →
  Groq → local Ollama)** for a review, and posts a Gitea review carrying a hidden
  `<!-- night-shift-review-task:v1 {…} -->` marker. Already non-Claude by design.
- **Remediator:** `scripts/tools/pr_review_remediator.py` — reads that marker off
  a PR, runs one remediation pass on the PR branch (`--agent <name>`, `--dry-run`,
  bounded max-attempts, refuses to touch `main`/`develop`).
- **Issue lifecycle + PR open:** `end_gitea_issue.py --open-pr`,
  `scripts/tools/gitea.py`. In **this repo (RTSColony)** the same lifecycle exists
  and additionally opens a GitHub review-mirror draft twin.
- **Skills for the missing passes** (portable, in AMPB `.agents/skills/`):
  `tdd` (red-green-refactor — this *is* step 1, "tdd-workflow"),
  `improve-codebase-architecture` (SOLID/CQRS), `review` (two-axis). This repo
  also has `/simplify` and `/code-review`.

## The genuine gaps (what Daedalus adds)

1. **Insert simplify + architecture passes** into the loop — the Night Shift loop
   today is implement → review → remediate, with no explicit `/simplify` or
   `/improve-architecture` step.
2. **A convergence rule** — the loop must stop on *no new findings*, not a blind
   fixed count.
3. **Port to a shared driver** — none of the Night Shift tooling is in RTSColony;
   rather than copy it per-repo, Daedalus wants one driver that serves any repo.
4. **Discord notify seam** — wire the "done, here's the PR" ping (the maintainer
   already has this pattern for Nyx; reuse it).
5. **Reviewer-backend seam** — make the cross-model reviewer pluggable: Gemini API
   (default, in-CI, proven) / Grok CLI / OpenClaw ChatGPT-web (flaky fallback).

## The loop (per ticket)

```
claim ticket (from a queue: sprint / epic / issue list)
  │
  ├─ 1. IMPLEMENT   /tdd  (red→green→refactor)         implementer = claude|grok|…
  │
  ├─ 2. SIMPLIFY    /simplify                          same implementer model
  │
  ├─ 3. ARCHITECT   /improve-architecture (SOLID/CQRS) same implementer model
  │
  ├─ open PR (draft)                                   end_gitea_issue.py --open-pr
  │
  ├─ 4. REVIEW      cross-model reviewer  ────────────  reviewer ≠ implementer
  │         (Gemini API default; Grok CLI; OpenClaw)    posts review + marker
  │
  ├─ 5. REMEDIATE   apply review findings ───┐          pr_review_remediator.py
  │         then GOTO 2 (simplify)           │          implementer model
  │                                          │
  │   ── convergence gate ───────────────────┘
  │      stop when: reviewer returns NO new actionable findings
  │      OR round == MAX_ROUNDS (hard ceiling, default 5)
  │      OR a pass fails the quality gate twice in a row (bail → human)
  │
  ├─ 5.5 NOTIFY     Discord: ticket, PR url, rounds, final verdict
  │
  └─ mark ticket done / release claim ; next ticket
```

### Convergence gate (the important bit)

A fixed "loop 5 times" wastes 3–5× the tokens on rounds that change nothing, and
can oscillate (reviewer asks for X; simplify undoes it; reviewer re-asks). Rule:

- The reviewer returns a **structured findings list** (it already emits the
  `night-shift-review-task:v1` marker — extend its payload with a
  `findings: []` array and a `blocking` boolean).
- **Converged** when a review round returns zero *new* blocking findings
  (dedupe against the previous round's findings by a stable hash, so a finding the
  remediator couldn't fix doesn't loop forever — those get surfaced to the human).
- `MAX_ROUNDS = 5` is a hard ceiling, not the target.
- **Two consecutive quality-gate failures** (build/tests red after a remediation
  pass) → stop and notify a human; do not keep burning rounds on a red tree.

### Model assignment rule

- **Implementer** (steps 1,2,3,5): the primary agent, default `claude`; falls
  back to `grok` (separate SuperGrok quota) when Claude is rate-limited — this is
  the whole point of the adapter chain.
- **Reviewer** (step 4): **must differ from the implementer** for that ticket.
  Default Gemini (API, robust). If the implementer *is* Gemini-backed, the review
  routes to Grok/another provider. Cross-model review is the design's core value —
  it catches each model's blind spots (e.g. one model's over-engineering flagged
  by another).

## Reviewer-backend seam

One interface, three backends, chosen by config/availability:

| Backend | Transport | Robustness | Cost | Use |
|---|---|---|---|---|
| **Gemini API** | HTTPS, in Gitea Actions | High (proven live) | Free tier | **default** |
| **Grok CLI** | `grok -p` headless | High | SuperGrok sub | when implementer≠grok and a 2nd opinion or Gemini-outage fallback is wanted |
| **OpenClaw → ChatGPT web** | browser scraping | Low (UI drift) | free | last-resort / optional 4th opinion only |

The existing `ai_pr_reviewer.js` provider chain (Gemini→mammouth→Groq→Ollama)
already realizes most of this; Daedalus formalizes "reviewer must differ from
implementer" and adds Grok-CLI and the OpenClaw fallback as chain entries.

## Where Daedalus runs (host layer)

Decided: the loop is driven by **Claude Code subagents** (`claude -p`) for each
step, reusing the existing skills directly — not a bespoke orchestrator. The
**Daedalus Hermes instance** (a duplicate of Nyx) is the host that: schedules/kicks
off runs, holds the Discord channel, and surfaces status. Duplicating Nyx into
Daedalus is tracked separately and is **blocked on QNAP host access** — see
[`00-nyx-recon.md`](00-nyx-recon.md). The loop driver itself can be developed and
tested from a normal checkout before the Hermes host is stood up.

## Build sequencing (proposed)

1. **This doc + the recon doc** (done).
2. **Stand up the loop driver in one repo, single ticket, human-in-the-loop:**
   a script that runs steps 1→5.5 for one issue with `--dry-run` on the
   remediation + notify, driving existing skills. Prove the convergence gate on a
   tiny ticket. (Good first real use here in RTSColony, or in AMPB where the
   reviewer already runs live.)
3. **Extend the reviewer marker** with the structured `findings[]`/`blocking`
   payload the convergence gate needs; teach the remediator to report per-finding
   outcomes.
4. **Wire the Discord notify seam** (reuse the Nyx pattern once its config is
   readable).
5. **Duplicate Nyx → Daedalus** on the QNAP host, ideally as
   **infrastructure-as-code** (a committed `docker-compose.yml` / env template in
   this `docs/daedalus/` tree, so the instance is reproducible and not a
   hand-clicked Container Station artifact). Blocked on QNAP access.
6. **Generalize to a queue** (sprint/epic chain) and, later, fold into the
   NightCrew central board as one worker.

## Open decisions (for the maintainer)

- **Home repo:** keep Daedalus docs/driver here in RTSColony, or give it its own
  repo like NightCrew was planned to? (These docs move with it either way.)
- **First target repo** for the live loop: RTSColony (spec-driven, strict gates)
  or AMPB (reviewer already runs live)?
- **IaC scope:** just the Hermes instance, or also the loop driver + reviewer
  workflow as committed, reproducible config?

## Hard rules Daedalus inherits (non-negotiable)

- **Never merge to `main`/`develop`.** Daedalus opens PRs; the maintainer merges.
- **One active ticket per worker**, enforced by the existing lock
  (`~/.config/pulse/locks/<repo>.json`).
- Respect each repo's style + workflow docs (e.g. this repo: no `!!`, no ternary,
  2-space JS, no "oracle" vocabulary; read `docs/style/*` and `AGENTS.md` first).
- Autonomous, outward-facing runs (headless agent, PR open, Discord post) are the
  kind of action that gets **human confirmation before first live trigger**.
