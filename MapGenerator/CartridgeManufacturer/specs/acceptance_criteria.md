# Acceptance Criteria

A build is considered successful when:

1. A `.wcar` file can be parsed without panics
2. WCAR chunks are validated against the spec
3. A valid CHK map is produced
4. Stratagus loads the CHK without errors
5. Headless simulation completes
6. Exit code reflects success or failure deterministically

Failure at any step must be observable and debuggable.
- acceptance_criteria.md
- assumptions.md
- context.md
- rust_style.md
- stratagus_harness_contract_v0_1.md
- prompt.txt (This prompt)

The system must provide useful logging to trace issues.