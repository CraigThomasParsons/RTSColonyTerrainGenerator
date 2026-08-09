# Repository Placement Guide

## Purpose

This guide shows how to insert the planning pack into the existing `RTSColonyTerrainGenerator/MapGenerator` setup without moving the current stages immediately.

## Recommended First Placement

```text
RTSColonyTerrainGenerator/
└── MapGenerator/
    ├── AGENTS.md
    ├── justfile
    ├── docs/
    │   ├── planning/
    │   │   ├── 00-README.md
    │   │   ├── 01-vision-and-principles.md
    │   │   ├── 02-target-architecture.md
    │   │   ├── 03-spec-to-code-workflow.md
    │   │   ├── 04-migration-roadmap.md
    │   │   ├── 05-bounded-contexts-and-ownership.md
    │   │   ├── 06-dafny-verification-strategy.md
    │   │   ├── 07-ci-quality-gates.md
    │   │   ├── 08-first-epic-verified-cell-to-tile.md
    │   │   └── 10-adr-001-specification-driven-mapgen.md
    │   ├── product/
    │   ├── contracts/
    │   ├── verification/
    │   └── adr/
    ├── features/
    ├── specifications/
    ├── src/
    ├── tests/
    ├── Heightmap/
    ├── WeatherAnalyses/
    ├── Tiler/
    ├── TreePlanter/
    ├── WorldFeatures/
    └── PathFinder/
```

Keep the existing stage folders where they are. Do not place them under `legacy/` until the new C# solution and adapters exist.

## Suggested Copy Commands

From the extracted planning-pack directory:

```bash
cd ~/Code/RTSColonyTerrainGenerator/MapGenerator

mkdir -p docs/planning
mkdir -p docs/product
mkdir -p docs/contracts
mkdir -p docs/verification
mkdir -p docs/adr
mkdir -p features
mkdir -p specifications
mkdir -p src
mkdir -p tests

cp /path/to/mapgen-spec-driven-planning/AGENTS.md ./AGENTS.md
cp /path/to/mapgen-spec-driven-planning/0*.md ./docs/planning/
cp /path/to/mapgen-spec-driven-planning/10-adr-001-specification-driven-mapgen.md ./docs/adr/ADR-001-specification-driven-mapgen.md
```

Adjust `/path/to/` to the extracted location.

## First Files to Promote from Planning into Active Work

### Product Requirement

Create:

```text
docs/product/tile-resolution/cell-to-tile-expansion.md
```

Extract the Product Requirement section from:

```text
docs/planning/08-first-epic-verified-cell-to-tile.md
```

### BDD Feature

Create:

```text
features/tile-resolution/cell-to-tile-expansion.feature
```

Copy and refine the Gherkin scenarios from Epic 1.

### Domain Contract

Create:

```text
docs/contracts/tile-resolution/cell-to-tile-expansion.contract.md
```

Copy the preconditions, postconditions, failure behaviour, and determinism rule.

### Dafny Specification

Create:

```text
specifications/TileResolution/CellExpansion.dfy
```

Begin with coordinate, bounds, cardinality, and uniqueness properties.

### C# Solution

A reasonable starting solution is:

```text
src/MapGen.Domain/
src/MapGen.Application/
src/MapGen.Contracts/
src/MapGen.Infrastructure/
tests/MapGen.Domain.Tests/
tests/MapGen.Application.Tests/
tests/MapGen.CompatibilityTests/
tests/MapGen.AcceptanceTests/
```

Do not move the current `Tiler` into these projects yet. First create an adapter and test its observable behaviour.

## First Integration Boundary

Introduce an application-facing interface:

```csharp
public interface ITileResolutionStage
{
    Task<TileResolutionResult> ExecuteAsync(
        TileResolutionRequest request,
        CancellationToken cancellationToken);
}
```

Implement it first with:

```text
ExistingTilerAdapter
```

Then build:

```text
CSharpTileResolutionStage
```

Both implementations can be run against the same fixture jobs by compatibility tests.

## Initial Branch

Suggested branch name:

```text
feature/spec-driven-mapgen-foundation
```

The branch should introduce:

- planning documents;
- `AGENTS.md`;
- empty active specification directories;
- initial solution projects;
- first Dafny verification command;
- first Epic 1 requirement and scenarios;
- no production stage replacement yet.

## Initial Commit Sequence

```text
docs: add specification-driven migration plan
build: add Dafny verification entry point
test: add cell-to-tile acceptance scenarios
feat: add tile-resolution domain value objects
spec: verify cell-to-tile expansion
feat: add CQRS command for tile-region resolution
test: compare cell expansion with existing tiler
```

This commit sequence keeps each change reviewable and teaches agents the intended progression.
