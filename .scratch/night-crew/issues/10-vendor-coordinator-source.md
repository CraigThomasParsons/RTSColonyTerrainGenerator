# 10 — Vendor TheNightCrew coordinator source into this repo

**What to build:** TheNightCrew coordinator (durable job board, Worker identities, atomic claims, Gitea fences, API, live dashboard) lives in this repository per the ticket-03 migration shape and still runs, scoped to coordination only (ADR 0007).

**Blocked by:** 01, 02, 03.

**Status:** ready-for-agent

- [ ] The coordinator source is present in-repo and its dashboard/API start locally.
- [ ] The coordinator/worker boundary from ADR 0007 is respected.
- [ ] A short doc records what was vendored, from where, and how to run it.
