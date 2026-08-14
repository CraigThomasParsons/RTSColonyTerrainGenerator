# 14 — MapGen verification gates wired

**What to build:** After the pipeline, the Slice's changes run the ticket-06 verification contract as a single pass/fail gate, and the result is recorded against the Slice's records.

**Blocked by:** 06, 13.

**Status:** ready-for-agent

- [ ] A green Slice passes; a Slice that breaks any blocking suite is stopped with failing evidence captured.
- [ ] Advisory-suite results are reported but non-blocking, per the ticket-06 contract.
- [ ] The gate result is recorded against the Slice.
