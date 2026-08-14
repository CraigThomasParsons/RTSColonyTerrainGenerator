# 01 — Beads ↔ Dolt authentication fixed

**What to build:** From this checkout, `bd ready` / `bd create` / `bd list` succeed against the configured Dolt server instead of failing with `Access denied`. Unblocks the machine-readable readiness half of the three-record model (ADR 0008).

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `bd ready` and `bd create` complete without an auth error against the configured server.
- [ ] The working credential/config path is documented so a fresh session reconnects without rediscovery.
- [ ] No secret is committed; credentials live outside version control.
