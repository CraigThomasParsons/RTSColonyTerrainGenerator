# Acceptance: <NN-slice-name>

<!-- Lifecycle steps 8 and 9: acceptance gates and PR evidence. -->

The gates that must hold before the slice's closing PR. This file feeds the PR
summary format in `AGENTS.md`.

## Behavioural Gates (dual profile)

- Feature file(s): `tests/bdd/features/<NN-slice-name>/*.feature`
- `npm run bdd:legacy` (the Legacy Pipeline): green — proves the contract is captured correctly.
- `npm run bdd:net` (new C# implementation): green — proves the slice is ported.
- Attach or link the cucumber report as PR evidence.

## Formal Gates (Dafny)

- `dafny verify specs/<...>.dfy`: all obligations discharged.
- `verification-report.md` present and honest about assumptions and exclusions.

## Compatibility Evidence

- Golden Jobs replayed: list `<id>`s and what was compared at the logical level.
- Differences found and their disposition (contract vs. accident; any normalization
  justified — never normalize away meaningful data).

## Test Evidence

- `dotnet test`: unit, property, architecture, integration suites green.
- New regression tests for any bug corrected en route.

## Manual Checks

Anything a human should eyeball: debug renders, WorldPreview/WorldSnapshot output,
map-document JSON samples. State what "looks right" means.

## Promotion

- [ ] Slice tag appended to `tests/bdd/net-ready.tags`
- [ ] Slice tag appended to `specs/dafny-ready.tags`
- [ ] No specification was weakened without human approval (or the weakening is named
      in the PR as a `Specification correction`).

## Known Gaps and Follow-Ups

What is knowingly not covered by these gates, and the issue(s) tracking it.
