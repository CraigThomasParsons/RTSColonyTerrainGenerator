# MapGenerator Specifications (Dafny)

This directory contains **design-time specifications** for the MapGenerator
pipeline, written in **Dafny**.

These specifications define **schemas, invariants, and contracts** that apply
across multiple pipeline stages and multiple programming languages.

They are **not** runtime dependencies.

---

## Purpose of This Folder

The `specs/` folder exists to answer one question:

> *“What is the authoritative shape and meaning of shared data in this pipeline?”*

Dafny is used here as a **formal design tool**, not as a production runtime.

Specifically, these specs are used to:

- Define **data schemas** shared across stages (e.g. logging events)
- Encode **invariants** that must always hold
- Act as **living documentation** that is stricter than prose
- Catch design mistakes early, before implementation diverges

---

## What Is NOT in Scope

This folder is **intentionally limited**.

It does **not** aim to:

- Generate production code for all stages
- Replace idiomatic implementations in Rust, C#, PHP, etc.
- Enforce contracts at runtime in every language
- Act as a shared library or framework

Any generated code from these specs is **disposable**.

---

## Generated Code Policy (Important)

Generated Dafny output (e.g. C#, DLLs, runtimes) is **not committed**.

Reasons:

- Dafny runtime interop is complex and language-specific
- Generated code is noisy and hard to review
- Runtime coupling caused more friction than value
- JSON and filesystem contracts already provide sufficient guarantees

The specs remain valuable even without generated artifacts.

---

## How These Specs Are Used

Typical workflow:

1. Write or update a Dafny spec in `specs/`
2. Verify it locally with:
   ```bash
   dafny verify <file>.dfy
   ```
3. Optionally generate code *temporarily* to:
   - sanity-check types
   - validate assumptions
4. Implement the same contract **idiomatically** in each stage language
5. Delete generated code

The Dafny spec remains as:
- the reference
- the guardrail
- the design record

---

## Example: Logging Specification

The logging spec defines:

- Required fields for a log event
- Valid log levels
- Structural invariants
- Assumptions shared by:
  - Heightmap (Rust)
  - Tiler (C#)
  - TreePlanter (PHP)
  - MapGenCtrl (TUI)

All stages emit **JSONL** logs that conform to this spec, without sharing runtime code.

---

## Design Philosophy

- **Contracts over code sharing**
- **Filesystem and JSON over RPC**
- **Idiomatic implementations over transpilation**
- **Verification once, pragmatism everywhere else**

If a pattern appears multiple times and proves stable, it may be abstracted later.
Until then, clarity and debuggability are prioritized over cleverness.

---

## Status

This folder is **intentionally stable and slow-moving**.

Changes here should be:
- deliberate
- reviewed carefully
- motivated by cross-stage needs

If you are unsure whether something belongs here, it probably doesn’t.
