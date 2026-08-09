<!-- Vendored verbatim from The-Pulse docs/adr/0013-dual-backend-parity-harness.md (local checkout ~/Code/The-Pulse), fetched 2026-07-13. Do not edit here; propose changes upstream and re-vendor. -->
# Dual-backend parity harness: Node oracle + .NET API side by side, observed and gated

**Status:** Accepted — the harness architecture for the Phase 5 .NET rewrite (PRD #118, ADR-0004),
decided in the Phase 5 PR #274 reset and recorded here as the first step of executing PRD #278
(2026-06-29). Supersedes the uncommitted external parity harness PR #274 relied on.

The .NET rewrite is verified against the live Node app as a behavioral **oracle**: the same scenario
must produce the same observable behavior on both backends. PR #274 claimed "21 BDD-verified
sprints" but its gate was an **external, uncommitted** harness (oracle on :5600, .NET on :5080) that
left no `.feature` files and no recorded evidence — green only in an agent's terminal, gone when the
process exited. Meanwhile the worktree-observability stack that should host such a gate (ADR-0009,
PRD #223) is **single-instance, single-backend**: `dev` and `net` are mutually exclusive compose
profiles, `scripts/dev-instance.ts` and the Instance manifest assume one `app`, and Vector scrapes
only the `…-app` container. And `net-api` is **observability-dark**: Serilog emits plain text (not
the #224 JSON contract), there is no correlation-id and no OpenTelemetry SDK, so none of its logs,
metrics, or traces reach the stack.

This ADR fixes the architecture so PRD #278 (and every per-context slice #124–#133 that runs inside
it) has a committed, telemetry-gated, reproducible parity check instead of re-inventing an ephemeral
one each time. It generalizes the ADR-0009 stack from one backend to two; it does not replace it.

## Decision

Run the Node oracle and the .NET API as **paired instances inside one worktree**, feed both into one
observability stack tagged by `backend`, and assert parity with **committed Gherkin scenarios + a
comparator that runs as a required CI check**. Delivered in ADR-0009-style vertical slices
(logs → metrics → traces/journeys/gate).

### 1. Paired instances, three compose projects, one shared network

One monorepo checkout builds both backends. The harness brings up **three** compose projects per
worktree, rather than the one ADR-0008/0009 used:

- `<wt>-oracle` — the `dev` profile: the TypeScript dev server (`app`) + its own ephemeral Postgres.
- `<wt>-net` — the `net` profile: the .NET API (`net-api`) + its own ephemeral Postgres.
- `<wt>-obs` — the `observability` profile as a **standalone project both app-projects target**:
  Vector + VictoriaLogs + VictoriaMetrics + VictoriaTraces.

The three projects are joined by a **shared external Docker network** the harness creates before
bring-up (and removes on teardown), so each app container resolves the collector in-network as
`vector:4318` regardless of which project owns it. Each backend keeps its **own** Postgres so the two
schemas/ids never collide. All storage stays ephemeral (`down -v`; db on tmpfs) per ADR-0008.

The existing single-backend `just dev-up` remains the **oracle-only** degenerate case of the same
machinery (one app-project + obs), so ADR-0009 flows (`drive-app`, `observe-app`, the #229 journeys)
keep working unchanged.

### 2. Multi-backend Instance manifest

Replace the single-`baseUrl` manifest with `backends: { oracle: { url, port }, net: { url, port } }`
alongside the shared `logsQlUrl` / `promQlUrl` / `traceQlUrl`. `scripts/dev-instance.ts`
orchestration, the `just` recipes, and the `drive-app` / `observe-app` skills read it. The change is
**back-compatible**: the oracle-only `dev-up` still records `baseUrl`/`appPort` so existing readers
keep working; the parity path additionally records the `backends` map.

### 3. Backend discrimination at the collector; `service.name` stays "pulse"

Both backends export under the **same** OTel `service.name = "pulse"` — they are one service with two
implementations, discriminated by a `backend` dimension, not two services. The `backend` value is
applied where each signal is collected, so the **oracle needs no code change** (editing `server/**`
is out of scope — it is the reference truth):

- **Logs** — both app containers carry the Docker label `pulse.backend=oracle|net` (set in compose,
  not app code). Vector's `docker_logs` source is scoped by that **label** (not by container name),
  and stamps a `backend` field onto every log event from the label. This is also what lets one Vector
  collect across the two app-projects.
- **Metrics & traces** — only the .NET side sets the OTLP **resource attribute `backend=net`**.
  Vector adds `backend=oracle` as the **default** when the attribute is absent, so the oracle's
  unmodified telemetry becomes `backend=oracle` and the .NET telemetry stays `backend=net`. No second
  OTLP port, no oracle edit.

LogsQL/PromQL/TraceQL queries then discriminate by `backend` (`backend=net` vs `backend=oracle`).

### 4. Identical reference data by business key

Seed both Postgres instances from the single source of truth `server/seed.ts` (drizzle-push + seed
host-side against each db). During migration both backends share that path; **EF baselines adopt the
schema as a no-op per ADR-0011 — there is no .NET seeder**. Because every surrogate id is a
`gen_random_uuid()` UUID, the two databases hold **divergent ids for the same logical rows**. The
comparator therefore resolves **business keys** to each backend's local ids and asserts referential
consistency, **never absolute id equality**: tenants by `slug`, users by `(tenant, email)`, events by
`(tenant, name)`, inquiry forms by `(tenant, slug)` (full table in PRD #278 / the comparator).

> **Implementation status (2026-06-29):** the committed comparator currently normalizes responses by
> *blanking* every surrogate id to one placeholder (plus volatile-field stripping and multiset array
> comparison) rather than *resolving* business keys — sufficient for the only shared endpoint today
> (`/api/health`, which carries no reference data), but it does **not** yet assert referential
> consistency (a mis-linked foreign key normalizes equal). Business-key resolution per this section
> lands with the reference-data scenarios in #124–#133. See `tests/bdd/parity/normalize.js` and its
> "known limitation" test.

### 5. .NET emission to the #224 contract (Layer 1, coordinates with #122)

`net-api` becomes a first-class citizen of the stack: Serilog single-line JSON matching the #224 log
contract (`ts, level, scope, message` + context + `err`), gated on `LOG_FORMAT=json`; a per-request
correlation-id (honor/echo `X-Request-Id` → `requestId`); the OpenTelemetry SDK (OTLP/HTTP-protobuf →
`vector:4318`, resource `service.name=pulse` + `backend=net`, the `pulse_startup_duration_milliseconds`
gauge, and journey-tagged spans `journey:<slug>`); plus a compose healthcheck the harness `--wait`
gates on. Production is unaffected: emission keys off the same env switches the Node side uses
(`LOG_FORMAT`, `OTEL_EXPORTER_OTLP_ENDPOINT`), which production never sets.

### 6. Committed, gating comparator

The parity scenarios are **committed Gherkin `.feature` files** and the comparator drives each against
**both** backends and asserts business-key-normalized response equality (plus, where useful,
telemetry/SLO assertions — the 2s-per-span SLO from #229 applied to `backend=net`). The comparator
runs **in CI as a required check** — the durable artifact #274 never produced. Golden response
captures on green are optional, for diffability. Oracle behavior is re-captured only on V1 drift
(Replit→main); a scheduled "re-run oracle + diff" check can flag drift.

> **Implementation status (2026-06-29).** The committed comparator + `.feature` scenarios ship, but
> the `parity.yml` workflow is **`workflow_dispatch`-only and NOT branch-protection-required** during
> the Actions cost freeze (see the workflow header and the 2026-06-17 cost-reduction note). Promoting
> it to the required check this section describes is a one-line follow-up once the freeze lifts (add the
> push/PR triggers + list "Parity Comparator" in branch protection / `posture-drift.yml` EXPECTED_CHECKS).
> Until then the SLO and parity assertions gate locally via `just parity-smoke`.

### Phases (vertical slices)

- **H0 — .NET telemetry foundation:** §5 emission on `net-api` + compose env + healthcheck.
- **H1 — logs parity:** §1 three-project orchestration + shared network, §2 manifest, §3 log-label
  scoping + `backend` field, §4 seed-both, `just parity-up`.
- **H2 — metrics parity:** .NET OTel metrics + §3 OTLP `backend` defaulting; PromQL by backend.
- **H3 — traces, journeys & the gate:** .NET journey spans, §6 comparator + `.feature` + required CI
  check + the 2s SLO on `backend=net`, `drive-app`/`observe-app` made backend-aware.

## Considered options

- **One compose project running both apps + obs (rejected).** Simpler networking (one network, no
  external network), but it couples the two backends' lifecycles and obscures the per-backend Postgres
  isolation the parity model depends on; it also diverges from the "paired but independent instances"
  framing the gate needs. The shared-network cost is small and bought back by clean isolation.
- **A separate observability stack per app (rejected).** Doubles the container footprint per worktree
  (already the binding constraint in ADR-0009) and defeats the goal — querying both backends *in one
  store* side by side. One stack, tagged by `backend`, is the point.
- **Discriminate by `service.name` (`pulse` vs `pulse-net`) (rejected).** Would make the two backends
  look like different services in every store and break the "same journey, two backends" query shape;
  `backend` as a dimension on one service keeps `journey=<slug> backend=<x>` symmetric.
- **A `.NET` seeder / migrating the seed to EF (rejected).** Two seeders is two sources of truth and
  the exact drift the oracle exists to catch; ADR-0011 already makes EF baselines no-op, so the one
  `server/seed.ts` path seeds both.
- **Record-and-replay as the primary gate (rejected, kept as fallback).** A captured-response replay
  is cheaper but stales silently against V1 drift; the live dual-backend comparison is the gate, with
  replay available only as a fallback if live dual-run proves too slow in CI.
- **Comparing surrogate ids (rejected — incorrect).** The ids are per-database UUIDs; equality would
  fail on every row. Business-key normalization is mandatory, not an optimization.

## Consequences

- **The harness generalizes from one backend to two.** `scripts/dev-instance.ts`, `scripts/harness/*`
  (manifest, compose, ports), the `justfile`, and the two skills all learn about `backend`; the
  manifest schema gains `backends`. Care is taken to keep the oracle-only path byte-compatible.
- **A required CI check now runs two containerized backends + the stack.** Heavier than the existing
  gates; mitigated by the ephemeral, per-worktree compose substrate (ADR-0008) and by the fallback
  option (record-and-replay) if live dual-run is too slow.
- **`net-api` joins the observability contract.** This also satisfies PRD #118's observability
  acceptance criteria and coordinates with #122 (cross-cutting emission). The #224 JSON contract is
  language-agnostic, so the log half survives cutover unchanged; the OTel half is rebuilt per context.
- **The oracle stays read-only.** All `backend` tagging for the oracle happens in compose/Vector, so
  `server/**` and `shared/schema.ts` are never edited — the reference truth is preserved.
- **Depends on** Track-0 foundation correction (#277, the rename/split + `net/docs` reconciliation,
  landed) for a coherent `net/` side, and on #122 for the cross-cutting emission wiring.
- **Lineage:** ADR-0004 (.NET rewrite), ADR-0008 (containerized dev), ADR-0009 (worktree
  observability), ADR-0010 (module structure), ADR-0011 (per-context schema adoption). Indexed in
  AGENTS.md.
