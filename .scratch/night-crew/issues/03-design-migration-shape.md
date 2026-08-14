# 03 — DESIGN: coordinator migration shape

**What to decide:** How TheNightCrew coordinator source is brought into this repository — vendored copy vs subtree/submodule vs extract-and-adapt — and what "in-repo and still runs" means for its build, data, and dashboard, honoring the ADR 0007 boundary.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Options weighed against the ADR 0007 coordinator/worker boundary and this repo's conventions.
- [ ] Decision recorded as an Accepted ADR.
- [ ] The vendoring impl ticket (10) references it.
