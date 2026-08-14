# 06 — DESIGN: verification contract

**What to decide:** Which MapGen suites are blocking vs advisory for a Slice — dual-reference BDD (legacy + net), Dafny verification, .NET tests, functional tests — and how the combined pass/fail gate result is recorded.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Each suite is classified blocking or advisory, with the rationale.
- [ ] Decision recorded as an Accepted ADR.
- [ ] The verification-gate impl ticket (14) references it.
