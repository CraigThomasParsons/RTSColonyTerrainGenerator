# 16 — Port AMPB reviewer + structured review-marker to the MapGen contract

**What to build:** AMPB's cross-model reviewer and structured review-marker are extracted and adapted to review a MapGen PR's diff and post a machine-ingestible findings marker (findings list + blocking flag) using MapGen vocabulary.

**Blocked by:** 15.

**Status:** ready-for-agent

- [ ] A MapGen PR receives an automated review posted as a structured, parseable marker.
- [ ] The reviewer runs a model distinct from the implementer and never mutates the PR branch.
- [ ] Secret-scanning and trusted-checkout properties from the AMPB original are preserved.
