# 04 — DESIGN: isolation & claim-recovery contract

**What to decide:** What isolation each claimed Slice gets (branch + worktree lifecycle) and what happens to it when a claim is lost or a Worker dies — release, reclaim, and cleanup semantics.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Claim-loss, Worker-death, and cleanup paths are specified with no ambiguous states.
- [ ] Decision recorded as an Accepted ADR.
- [ ] The Worker skeleton impl ticket (12) references it.
