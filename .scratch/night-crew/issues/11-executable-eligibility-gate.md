# 11 — Executable eligibility gate (implements ADR 0009)

**What to build:** A fail-closed evaluator that, given a Slice, returns eligible only when every ADR 0009 condition holds: Gitea issue open with `status: planned` + `night-crew: approved`, explicit acceptance criteria, an existing linked Planning Document, a top-level Bead that points back and reports ready, and no conflicting claim.

**Blocked by:** 01, 02, 10.

**Status:** ready-for-agent

- [ ] Given an approved well-formed Slice the gate returns eligible; removing any single condition returns not-eligible with a specific reason.
- [ ] Missing, unavailable, or contradictory evidence fails closed.
- [ ] The gate never writes the approval label itself.
