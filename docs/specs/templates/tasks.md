# Tasks: <NN-slice-name>

<!-- Lifecycle steps 7 and 8: implementation and tests, as thin ordered slices. -->

Implementation slices in execution order. Each task is small enough to validate on its
own, names its outputs, and names the command that proves it. Update this file as
tasks complete or as reality corrects the plan (same change as the code).

## Task 1 — <name>

- **What:** one or two sentences.
- **Outputs:** files/projects created or changed.
- **Validation:** the exact command (`dafny verify specs/...`, `dotnet test --filter ...`,
  `npm run bdd:legacy`, ...) and its expected result.
- **Status:** todo | in progress | done.

## Task 2 — <name>

...

## Suggested Task Order for a Standard Slice

1. Capture Golden Job fixtures from the legacy stage (baseline evidence).
2. Author the feature file(s) and step definitions; prove green on the `legacy` profile.
3. Write the Dafny model or reference; `dafny verify` green; draft `verification-report.md`.
4. Define command/query contracts.
5. Implement the C# domain (value objects, invariants, typed failures).
6. Unit and property tests (properties drawn from the Dafny contract).
7. Compatibility tests against Golden Jobs (and Dafny reference outputs, if Level B).
8. Integration wiring (adapters, filesystem lanes) and integration tests.
9. Same feature file green on the `net` profile.
10. Promotion: append the slice tag to `tests/bdd/net-ready.tags` and
    `specs/dafny-ready.tags` in the closing PR.
