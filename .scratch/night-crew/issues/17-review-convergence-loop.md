# 17 — Bounded review-convergence loop

**What to build:** One bounded loop that requests review, ingests structured findings, remediates on the PR branch, re-runs the full gate-14 verification, and repeats until converged or the ceiling is hit per the ticket-07 contract, escalating to a human on repeated failure.

**Blocked by:** 07, 14, 16.

**Status:** ready-for-agent

- [ ] The loop stops on no-new-blocking-findings, at the ceiling, and on the escalation trigger — never loops unbounded.
- [ ] Each remediation pass re-runs the full gate-14 verification before the next review.
- [ ] Escalation surfaces to a human with the outstanding findings.
