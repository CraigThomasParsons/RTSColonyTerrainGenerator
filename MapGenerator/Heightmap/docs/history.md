
---

# 📄 `history.md`

```md
# Heightmap Generator – Development History

## Summary

This document records where development left off after a context loss
(ChatGPT UI history truncation + local PC restart), to prevent repetition
and loss of momentum.

---

## Key Decisions (Already Made)

- File-based queue chosen over message brokers
- systemd selected for orchestration
- Bash chosen as worker glue
- Rust chosen for heightmap engine
- Deterministic generation required
- One job → one output file rule enforced
- Verbose, commented Rust code style enforced

These decisions are considered final unless explicitly revisited.

---

## Major Milestones Reached

### Heightmap Engine Implemented (Rust)

A working `main.rs` exists that:

- Defines a `HeightmapJob` struct via `serde::Deserialize`
- Parses CLI arguments:
  - `--job-file`
  - `--output-file`
- Uses `ChaCha8Rng` with a fixed seed
- Implements a fault-line algorithm:
  - Random line per iteration
  - Signed cross-product side test
  - Positive / negative displacement
- Accumulates signed height values
- Normalizes values to 0–255
- Writes a binary heightmap file
- Logs progress and handles edge cases

This is considered **Heightmap Engine v0.1**.

---

## Last Known Code State

The active `main.rs` contained:

- Deterministic fault-line generation
- Fully commented geometry math
- Explicit handling of degenerate lines
- Safe normalization logic
- Binary output write via `fs::write`

The engine is functional and not a stub.

---

## Interruption Event

- PC restart occurred
- Chat UI lost a large portion of conversation history
- Docker Compose debugging had to be repeated
- Heightmap engine code itself was **not lost**

This document exists to prevent recurrence of this issue.

---

## Exact Point Where Work Paused

At the time of interruption:

- Heightmap engine code was complete and compiling
- Docker Compose for Heightmap API was fixed
- API-to-inbox flow existed previously
- The **next planned step** had not yet been executed

---

## Planned Next Steps (In Order)

1. Freeze the job JSON schema as v1
2. Ensure API writes JSON matching `HeightmapJob`
3. Write Bash worker to:
   - Claim job files
   - Invoke heightmap-engine
   - Write output to outbox
4. Add systemd `.path` and `.service` units
5. Verify end-to-end queue execution
6. Extend engine with:
   - Layer classification
   - Fault-line metadata output

---

## Developer Notes

- This project benefits from explicit documentation checkpoints
- Future work should update this file when milestones are reached
- Treat this file as a recovery anchor after interruptions
