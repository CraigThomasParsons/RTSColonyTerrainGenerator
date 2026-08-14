# 05 — DESIGN: pipeline phase contract

**What to decide:** The LaunchKit pipeline's phase order (TDD → simplify → architecture → code-review), each phase's completion sentinel, and what a phase failure or stall does (retry, abort, escalate).

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Phase order, per-phase sentinels, and failure/stall handling are specified.
- [ ] Decision recorded as an Accepted ADR.
- [ ] The LaunchKit impl ticket (13) references it.
