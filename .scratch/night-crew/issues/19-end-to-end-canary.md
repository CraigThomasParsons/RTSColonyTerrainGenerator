# 19 — End-to-end canary Slice

**What to build:** One real, trivial MapGen Slice flows the entire path — planning + approval, claim + isolation, pipeline, verification, PR + mirror, review convergence, merge, reconcile, notify — under real human approval, meeting the ticket-09 pass criteria.

**Blocked by:** 09, 18.

**Status:** ready-for-agent

- [ ] A single trivial Slice completes the full path with `night-crew: approved` applied by a human.
- [ ] The ticket-09 pass criteria are met and the run's evidence is captured as the integration proof.
- [ ] Any stage failure is diagnosable from the captured evidence.
