# 12 — MapGen Night-Crew Worker skeleton (claim + isolation)

**What to build:** A MapGen Night-Crew Worker that claims an eligible Slice via the coordinator's atomic claim and prepares its isolated branch + worktree per the ticket-04 contract, recording claim and progress — no coding-agent execution yet.

**Blocked by:** 04, 10, 11.

**Status:** ready-for-agent

- [ ] The Worker claims exactly one eligible Slice, creates its isolated branch and worktree, and reports the claim.
- [ ] Two Workers cannot hold the same Slice; a released/failed claim recovers per the ticket-04 contract.
- [ ] Claim and progress are visible to the coordinator.
