# Quality-gate surface for the spec-driven conversion (docs: mapgen-spec-driven-planning/07-ci-quality-gates.md).
# Install `just` via: sudo pacman -S just
#
# MapGen.slnx scopes dotnet to the new spec-driven projects; the legacy Tiler csproj
# currently fails to build (pre-existing, tracked separately) and stays out of the gates
# until its slice migrates it.

default:
    just --list

# Gate 1 — formatting
format:
    dotnet format MapGen.slnx

format-check:
    dotnet format MapGen.slnx --verify-no-changes

# Gate 2 — build
build:
    dotnet build MapGen.slnx

# Gate 3 — Dafny verification (every .dfy under specs/ must verify)
verify:
    find specs -name '*.dfy' -print0 | xargs -0 -n1 dafny verify

# Gate 4 — domain unit + property tests
test-unit:
    dotnet test tests/MapGen.Domain.Tests
    dotnet test tests/MapGen.Application.Tests

# Gate 5 — architecture tests (dependency direction is enforced, not suggested)
test-architecture:
    dotnet test tests/MapGen.ArchitectureTests

# Gate 6 — HTTP endpoint tests (MapGen.Api against the real application layer)
test-api:
    dotnet test tests/MapGen.Api.Tests

# Gate 7 — legacy-vs-replacement compatibility
test-compatibility:
    dotnet test tests/MapGen.CompatibilityTests

# Gate 8 — BDD acceptance (cucumber-js; same Gherkin, either target)
bdd-smoke:
    npm run bdd:smoke

bdd-legacy:
    npm run bdd:legacy

bdd-net:
    npm run bdd:net

# The whole gate ladder, in CI order.
quality:
    just format-check
    just build
    just verify
    just test-unit
    just test-architecture
    just test-api
    just test-compatibility
    just bdd-smoke
    just bdd-legacy
    just bdd-net

# Run the legacy pipeline end to end (filesystem is the source of truth).
run-legacy width='248' height='248':
    python -m tools.mapgenctl run --width {{width}} --height {{height}}
