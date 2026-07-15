// cucumber-js profiles — target selection for the dual-reference parity loop.
// -p legacy -> the existing filesystem pipeline (Rust/C#/PHP/Kotlin stages, the baseline)
// -p net    -> the new C# CQRS implementation (MapGen.* — grows as slices are promoted)
// Mirrors ThePulseProject/PulseClient/cucumber.mjs; see docs/adr/0003-cucumber-js-bdd-runner.md.
const common = {
  paths: ['tests/bdd/features/**/*.feature'],
  import: ['tests/bdd/support/**/*.js', 'tests/bdd/steps/**/*.js'],
  tags: 'not @wip',
  parallel: 2,
};

// @net-only marks documented profile asymmetries (e.g. per-cell rejection — the legacy
// stage has no request surface to reject a coordinate). Only the net profile runs them.
export default { ...common, tags: 'not @wip and not @net-only' };
export const legacy = { ...common, tags: 'not @wip and not @net-only', worldParameters: { target: 'legacy' } };
export const net    = { ...common, worldParameters: { target: 'net' } };
export const smoke  = { ...common, tags: '@slice-00-cross-cutting and not @wip' };
