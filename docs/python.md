# Python Coding Style & Commenting Conventions (Project-Aligned)

This document defines the required Python coding style for all MapGenerator
and pipeline tooling.

The goals are clarity, explicitness, and long-term maintainability. Favor
boring, readable code over cleverness.

---

## Core Philosophy

- Code must be understandable months later without external context.
- Readability beats brevity; avoid terse or clever constructs.
- Descriptive names everywhere; avoid abbreviations.
- Fail fast, guard early, and be explicit about errors.
- Keep modules focused: one clear responsibility per file.

---

## Naming Conventions (LOCKED)

- Functions and variables: `snake_case`, descriptive, multi-word.
- Classes: `PascalCase` with explicit meaning.
- Constants: `UPPER_SNAKE_CASE`.
- Avoid single-letter variables (except for tiny comprehensions).

Good:

```python
output_directory = resolve_output_directory()
start_zone_candidates = select_start_zones(tiles)
```

Bad:

```python
out = resolve_output_directory()
zs = select_start_zones(tiles)
```

---

## File & Module Structure

- One responsibility per file; avoid mixed concerns.
- Keep files small and focused on a single concept.
- Avoid hidden side effects on import.

---

## Commenting Rules (CRITICAL)

- Target: a meaningful comment every 3–5 logical statements.
- Comments explain **why** more than **what**. Avoid narrating syntax.
- Document guard clauses: why the early exit exists.
- Use block comments to describe module intent and boundaries.
- Keep examples current; delete stale comments.

Examples:

```python
# Reject empty payloads to prevent invalid jobs from being queued.
if not payload_text.strip():
    raise ValueError("Empty payload")
```

---

## Function Docblocks (MANDATORY)

Every function must include a docblock-style docstring with these sections:

1. **Description** — what it does and why it exists.
2. **Required State** — assumptions or invariants required to run safely.
3. **Usage** — how/when to call the function.
4. **Parameters** — name + type, and meaning.
5. **Returns** — type and meaning.
6. **Other I/O** — files read/written, logs emitted, or side effects.

Template:

```python
"""
Description:
    ...
Required State:
    ...
Usage:
    ...
Parameters:
    name (type): description
Returns:
    type: description
Other I/O:
    - files: ...
    - logs: ...
"""
```

---

## Error Handling

- Fail fast with guard clauses; avoid deep nesting.
- Never ignore exceptions; log and return explicit failure codes.
- Prefer returning clear status codes over silent failures.

---

## JSON & I/O

- Always validate external input before use.
- Pretty-print JSON when writing to disk unless size is critical.
- Prefer `Path` from `pathlib` for filesystem operations.

---

## Formatting Rules

- 4 spaces per indent.
- One statement per line.
- Blank lines separate logical sections.
- Keep lines readable; avoid long chained expressions.

---

## Forbidden Practices

- 🚫 Single-letter variable names outside of tiny scopes.
- 🚫 Abbreviations that hide intent.
- 🚫 Deeply nested conditionals when guard clauses suffice.
- 🚫 Silent error ignoring.
- 🚫 Clever one-liners that obscure intent.
- 🚫 Mixing unrelated concerns in a single function.

---

Final rule: if a future reader must guess intent, the code is wrong. Clarity is the priority.
