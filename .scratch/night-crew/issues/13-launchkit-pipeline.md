# 13 — LaunchKit pipeline wired into the Worker

**What to build:** On a claimed Slice's worktree, the Worker drives the LaunchKit sentinel-gated tmux pipeline through the ticket-05 phase contract, advancing on completion sentinels and classifying worker state deterministically.

**Blocked by:** 05, 12.

**Status:** ready-for-agent

- [ ] A claimed trivial Slice runs end-to-end through all phases in its worktree.
- [ ] Phase advancement is driven by the sentinels from the ticket-05 contract.
- [ ] A stalled or failed phase is detected and surfaced rather than hanging.
